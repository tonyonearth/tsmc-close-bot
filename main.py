from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from typing import Any
from zoneinfo import ZoneInfo

import requests

TWSE_STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
TAIPEI_TZ = ZoneInfo("Asia/Taipei")


@dataclass
class StockDailyRecord:
    trade_date: date
    trade_volume: str
    trade_value: str
    opening_price: str
    highest_price: str
    lowest_price: str
    closing_price: str
    change: str
    transaction_count: str
    note: str = ""


def roc_date_to_gregorian(value: str) -> date:
    """Convert ROC date like '114/03/20' to Gregorian date."""
    parts = value.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Unexpected ROC date format: {value!r}")
    roc_year, month, day = map(int, parts)
    return date(roc_year + 1911, month, day)


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def fetch_monthly_stock_data(stock_no: str, target_day: date) -> dict[str, Any]:
    month_anchor = target_day.strftime("%Y%m01")
    params = {
        "response": "json",
        "date": month_anchor,
        "stockNo": stock_no,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; tw-stock-close-bot/1.0)",
        "Accept": "application/json,text/plain,*/*",
    }
    response = requests.get(TWSE_STOCK_DAY_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()

    stat = str(payload.get("stat", "")).strip()
    if stat and stat.upper() != "OK":
        raise RuntimeError(f"TWSE returned non-OK stat: {stat}")

    return payload


def parse_records(payload: dict[str, Any]) -> list[StockDailyRecord]:
    rows = payload.get("data") or []
    records: list[StockDailyRecord] = []

    for row in rows:
        if not isinstance(row, list) or len(row) < 9:
            continue
        note = row[9] if len(row) > 9 else ""
        records.append(
            StockDailyRecord(
                trade_date=roc_date_to_gregorian(row[0]),
                trade_volume=str(row[1]),
                trade_value=str(row[2]),
                opening_price=str(row[3]),
                highest_price=str(row[4]),
                lowest_price=str(row[5]),
                closing_price=str(row[6]),
                change=str(row[7]),
                transaction_count=str(row[8]),
                note=str(note),
            )
        )

    records.sort(key=lambda r: r.trade_date)
    return records


def pick_latest_record(records: list[StockDailyRecord], today: date) -> StockDailyRecord | None:
    eligible = [r for r in records if r.trade_date <= today]
    return eligible[-1] if eligible else None


def build_email(stock_name: str, stock_no: str, today: date, latest: StockDailyRecord | None) -> tuple[str, str]:
    if latest is None:
        subject = f"[台股通知] {stock_name}({stock_no}) {today.isoformat()} 查無資料"
        body = (
            f"{stock_name}({stock_no})\n"
            f"查詢日期：{today.isoformat()}\n\n"
            "今天未取得任何成交資料。\n"
            "可能原因：\n"
            "1. 當月尚未有成交資料\n"
            "2. 股票代碼錯誤\n"
            "3. TWSE API 暫時異常\n\n"
            f"資料來源：{TWSE_STOCK_DAY_URL}\n"
        )
        return subject, body

    if latest.trade_date == today:
        subject = (
            f"[台股收盤] {stock_name}({stock_no}) "
            f"{latest.trade_date.isoformat()} 收盤 {latest.closing_price}"
        )
        body = (
            f"{stock_name}({stock_no}) 今日收盤通知\n"
            f"交易日期：{latest.trade_date.isoformat()}\n"
            f"開盤價：{latest.opening_price}\n"
            f"最高價：{latest.highest_price}\n"
            f"最低價：{latest.lowest_price}\n"
            f"收盤價：{latest.closing_price}\n"
            f"漲跌價差：{latest.change}\n"
            f"成交股數：{latest.trade_volume}\n"
            f"成交金額：{latest.trade_value}\n"
            f"成交筆數：{latest.transaction_count}\n"
            f"註記：{latest.note or '無'}\n\n"
            f"資料來源：{TWSE_STOCK_DAY_URL}\n"
        )
    else:
        subject = f"[台股休市/無當日資料] {stock_name}({stock_no}) {today.isoformat()}"
        body = (
            f"{stock_name}({stock_no})\n"
            f"今日日期：{today.isoformat()}\n"
            "今天沒有新的成交資料，可能是週末、國定假日、颱風停市，或 TWSE 尚未更新。\n\n"
            f"最近一個成交日：{latest.trade_date.isoformat()}\n"
            f"最近收盤價：{latest.closing_price}\n"
            f"最近漲跌價差：{latest.change}\n"
            f"最近成交股數：{latest.trade_volume}\n\n"
            f"資料來源：{TWSE_STOCK_DAY_URL}\n"
        )

    return subject, body


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    email_from: str,
    email_to: str, # 這裡傳進來會是 "a@gmail.com, b@gmail.com" 這樣的字串
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_from
    # message["To"] = email_to # EmailMessage 會自動處理逗點分隔的字串
    message["To"] = "已寄送"#email_from # 給自己，或寫「群組通知」
    message["Bcc"] = email_to # 將多個收件人放在密件抄送
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


def main() -> None:
    today = datetime.now(TAIPEI_TZ).date()

    stock_no = get_env("STOCK_NO", "2330")
    stock_name = get_env("STOCK_NAME", "台積電")

    smtp_host = get_env("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(get_env("SMTP_PORT", "587"))
    smtp_username = get_env("SMTP_USERNAME", required=True)
    smtp_password = get_env("SMTP_PASSWORD", required=True)
    email_from = get_env("EMAIL_FROM", smtp_username)
    email_to = get_env("EMAIL_TO", required=True)

    payload = fetch_monthly_stock_data(stock_no=stock_no, target_day=today)
    records = parse_records(payload)
    latest = pick_latest_record(records, today)
    subject, body = build_email(stock_name, stock_no, today, latest)

    send_email(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        email_from=email_from,
        email_to=email_to,
        subject=subject,
        body=body,
    )

    print(subject)


if __name__ == "__main__":
    main()
