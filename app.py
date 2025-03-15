from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import os
import json
import datetime
import schedule
import time
import threading
import matplotlib.pyplot as plt

app = Flask(__name__)

# 設定 LINE BOT
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 記帳 & 行程的資料存取
RECORDS_FILE = "records.json"
USERS_FILE = "users.json"

# 載入已註冊的使用者
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except json.JSONDecodeError:
            return []
    return []

# 存儲已註冊的使用者
def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 載入記帳 & 行程
def load_data():
    if os.path.exists(RECORDS_FILE):
        try:
            with open(RECORDS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except json.JSONDecodeError:
            return []
    return []

# 存儲記帳 & 行程
def save_data(records):
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK", 200

# 產生日曆圖片
def generate_calendar_image(records):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    plt.figure(figsize=(6, 4))
    plt.text(0.1, 0.9, f"📅 {today}", fontsize=14, weight="bold")

    y_pos = 0.7
    for record in records:
        plt.text(0.1, y_pos, f"🔹 {record}", fontsize=12)
        y_pos -= 0.1

    plt.axis("off")
    filename = "calendar.png"
    plt.savefig(filename, bbox_inches="tight")
    return filename

# 設定每天 06:00 自動推送當日行程
def send_daily_schedule():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    users = load_users()
    records = load_data()  # 讀取最新的資料
    message = "📅 今日行程 & 記帳 📅\n"
    records_today = [r["description"] for r in records if r["datetime"].startswith(today)]

    if records_today:
        message += "\n".join([f"🔹 {r}" for r in records_today])
    else:
        message += "📌 今天沒有任何記錄"

    for user_id in users:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))

# 設定排程
schedule.every().day.at("06:00").do(send_daily_schedule)

def schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=schedule_runner, daemon=True).start()

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    user_id = event.source.user_id
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    users = load_users()
    records = load_data()  # 讀取最新的記帳 & 行程資料

    if user_id not in users:
        users.append(user_id)
        save_users(users)
        line_bot_api.push_message(user_id, TextSendMessage(text="✅ 你已成功註冊！每日 6:00 會收到行程提醒！"))

    if "元" in user_input:
        parts = user_input.split()
        if len(parts) >= 2:
            try:
                amount = float(parts[1].replace("元", ""))
                category = parts[2] if len(parts) > 2 else "未分類"
                records.append({
                    "type": "消費",
                    "description": parts[0],
                    "amount": amount,
                    "category": category,
                    "datetime": f"{today} {datetime.datetime.now().strftime('%H:%M')}"
                })
                save_data(records)
                response = f"已記錄消費：{parts[0]}，金額：{amount} 元，類別：{category}"
            except ValueError:
                response = "請輸入有效的金額，例如：午餐 120元 食物"
    
    elif "點" in user_input or "週" in user_input or "日" in user_input:
        records.append({
            "type": "行程",
            "description": user_input,
            "datetime": f"{today} {datetime.datetime.now().strftime('%H:%M')}"
        })
        save_data(records)
        response = f"已記錄行程：{user_input}"

    elif user_input == "日曆":
        records_today = [r["description"] for r in records if r["datetime"].startswith(today)]
        if not records_today:
            response = "📌 今天沒有任何記錄"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
            return
        
        calendar_image = generate_calendar_image(records_today)
        message = ImageSendMessage(
            original_content_url=f"https://你的-render-網址/{calendar_image}",
            preview_image_url=f"https://你的-render-網址/{calendar_image}"
        )
        line_bot_api.reply_message(event.reply_token, message)
    
    else:
        response = "請輸入「日曆」來查看今日記錄"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
