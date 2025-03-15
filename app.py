from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import json
import datetime

app = Flask(__name__)

# 設定你的 LINE BOT 設定（需填入自己的 Token 和 Secret）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

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

@app.route("/", methods=["GET"])
def home():
    return "LINE 智能管家已啟動！"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK", 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    response = "無法識別，請輸入記帳或行程資訊。"

    # 判斷是記帳還是行程
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
                    "datetime": now
                })
                save_data()
                response = f"已記錄消費：{parts[0]}，金額：{amount} 元，類別：{category}，時間：{now}"
            except ValueError:
                response = "請輸入有效的金額，例如：午餐 120元 食物"
    elif "點" in user_input or "週" in user_input or "日" in user_input:
        records.append({
            "type": "行程",
            "description": user_input,
            "datetime": now
        })
        save_data()
        response = f"已記錄行程：{user_input}，時間：{now}"
    elif "查帳" in user_input:
        total = sum(r["amount"] for r in records if r["type"] == "消費")
        response = f"目前總消費金額：{total} 元"
    elif "行程" in user_input:
        event_list = [r["description"] for r in records if r["type"] == "行程"]
        response = "你的行程：\n" + "\n".join(event_list) if event_list else "目前沒有行程記錄。"

    line_bot_api.reply_message(event.reply_token, 
TextSendMessage(text=response))

if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000)

