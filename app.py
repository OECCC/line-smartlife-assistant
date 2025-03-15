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

# 設定你的 LINE BOT 設定（需填入自己的 Token 和 Secret）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_USER_ID = "你的 LINE 使用者 ID"  # 你需要填入你的 LINE 個人 ID

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 儲存記帳 & 行程的資料
records = []

def save_data():
    with open("records.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def load_data():
    global records
    if os.path.exists("records.json"):
        with open("records.json", "r", encoding="utf-8") as f:
            records = json.load(f)

# 設定每天 06:00 自動推送當日行程
def send_daily_schedule():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    records_today = [r["description"] for r in records if r["datetime"].startswith(today)]
    
    message = f"📅 今日行程 & 記帳 📅\n"
    if records_today:
        message += "\n".join([f"🔹 {r}" for r in records_today])
    else:
        message += "📌 今天沒有任何記錄"
    
    line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=message))

# 設定排程
schedule.every().day.at("06:00").do(send_daily_schedule)

def schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每 60 秒檢查一次

# 啟動排程
threading.Thread(target=schedule_runner, daemon=True).start()

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if user_input == "日曆":
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
    load_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
