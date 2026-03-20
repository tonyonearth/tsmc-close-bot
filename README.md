# 台積電每日收盤 Email Bot

這個專案會在每個 **週一到週五的台北時間 14:10** 自動執行：

1. 查詢台股 **台積電（2330）** 當月成交資料
2. 取出「今天」的成交結果
3. 用 Email 將收盤資訊寄給你
4. 若今天沒有新成交資料，則寄出「休市 / 無當日資料」通知

## 專案結構

```text
.
├─ .github/workflows/tsmc-close-notify.yml
├─ .env.example
├─ .gitignore
├─ main.py
├─ README.md
└─ requirements.txt
```

## 本機測試

### 1. 建立虛擬環境

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 改用 .venv\Scripts\activate
```

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

你可以參考 `.env.example`：

```bash
export SMTP_USERNAME='your_gmail@gmail.com'
export SMTP_PASSWORD='your_16_digit_app_password'
export EMAIL_FROM='your_gmail@gmail.com'
export EMAIL_TO='your_gmail@gmail.com'
export STOCK_NO='2330'
export STOCK_NAME='台積電'
```

### 4. 執行

```bash
python main.py
```

---

## 部署到 GitHub Actions

### 1. 建立 GitHub Repository

例如建立：

```text
tsmc-close-bot
```

然後把這個專案全部推上去。

### 2. 建立 GitHub Secrets

到 GitHub Repository：

```text
Settings → Secrets and variables → Actions → New repository secret
```

新增以下 secrets：

- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

### 3. 啟用 Gmail App Password

若你用 Gmail / Google Workspace SMTP：

1. 先開啟 Google 帳號的 **2-Step Verification**
2. 建立 **App Password**
3. 把那組 16 碼密碼填進 `SMTP_PASSWORD`

### 4. 手動測試一次

到：

```text
GitHub → Actions → tsmc-close-notify → Run workflow
```

先確認你能收到信。

### 5. 等待排程自動執行

此 workflow 已設定：

- 週一到週五
- 台北時間 14:10

---

## 可自訂項目

### 改股票

把 workflow 中：

```yaml
STOCK_NO: '2330'
STOCK_NAME: '台積電'
```

換成別的上市股票即可。

### 改收信人

只要修改 `EMAIL_TO` secret。

### 改寄件方式

若你不想用 Gmail，也可以改成其他 SMTP 服務，只要調整：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

---

## 注意事項

1. GitHub Actions 的排程偶爾可能延遲。
2. 若使用 **public repository**，GitHub 可能在長時間沒有活動後停用 scheduled workflow。
3. 本專案目前使用台灣證交所資料來源，適合上市股票（TWSE）。

---

## 授權

MIT（你可以自行補上 LICENSE）
