from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from collections import defaultdict
from openai import OpenAI
import os

app = Flask(__name__)

line_bot_api = LineBotApi(
    os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
)

handler = WebhookHandler(
    os.environ["LINE_CHANNEL_SECRET"]
)

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

chat_memory = defaultdict(list)

SYSTEM_PROMPT = """
請使用繁體中文回答。

你是一位台灣網友。

風格：
- Threads
- Dcard
- PTT
- 自然口語
- 有自己的觀點

口頭禪：
- 偶爾自然使用「確實」
- 遇到衝動話題可說「冷靜」
- 遇到離譜事情可說「法克」

規則：

- 不要使用簡體中文
- 不要自稱AI
- 不要幻想資料
- 如果需要最新資訊，請先搜尋網路
- 如果資訊不足，先提問
"""

@app.route("/")
def home():
    return "GPT-5.4 Mini Bot Running"

@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    user_text = event.message.text.strip()

    # 群組
    if hasattr(event.source, "group_id"):

        room_id = event.source.group_id

        triggers = [
            "@gpt",
            "@bot",
            "@ai"
        ]

        trigger_found = False

        for trigger in triggers:

            if user_text.lower().startswith(trigger):

                user_text = user_text[len(trigger):].strip()

                trigger_found = True
                break

        if not trigger_found:
            return

    # 多人聊天室
    elif hasattr(event.source, "room_id"):

        room_id = event.source.room_id

        triggers = [
            "@gpt",
            "@bot",
            "@ai"
        ]

        trigger_found = False

        for trigger in triggers:

            if user_text.lower().startswith(trigger):

                user_text = user_text[len(trigger):].strip()

                trigger_found = True
                break

        if not trigger_found:
            return

    # 私訊
    else:

        room_id = event.source.user_id

    # reset
    if user_text.lower() == "reset":

        chat_memory[room_id] = []

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="確實，我失憶了 XD"
            )
        )

        return

    # status
    if user_text.lower() == "status":

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"""📊 GPT 狀態

記憶數量：{len(chat_memory[room_id])}
模型：GPT-5.4 Mini

目前正常運作中 XD"""
            )
        )

        return

    # 今日摘要
    if user_text == "今日摘要":

        summary_text = "\n".join(
            [
                msg["content"]
                for msg in chat_memory[room_id]
                if msg["role"] == "user"
            ]
        )

        try:

            response = client.responses.create(
                model="gpt-5.4-mini",
                input=[
                    {
                        "role": "system",
                        "content": """
請整理群組聊天內容。

格式：

📌 今日重點
😂 今日幹話
🎯 今日結論

請使用繁體中文。
"""
                    },
                    {
                        "role": "user",
                        "content": summary_text
                    }
                ]
            )

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=response.output_text[:5000]
                )
            )

        except Exception as e:

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"法克，摘要失敗 XD\n{str(e)[:200]}"
                )
            )

        return

    # 記憶使用者訊息
    chat_memory[room_id].append(
        {
            "role": "user",
            "content": user_text
        }
    )

    # 保留最近50則
    chat_memory[room_id] = chat_memory[room_id][-50:]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(chat_memory[room_id])

    try:

        response = client.responses.create(
            model="gpt-5.4-mini",
            tools=[
                {
                 "type": "web_search"
                }
            ],
    input=messages
        )

        reply_text = response.output_text

        # GPT回覆加入記憶
        chat_memory[room_id].append(
            {
                "role": "assistant",
                "content": reply_text
            }
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=reply_text[:5000]
            )
        )

    except Exception as e:

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"法克，出事了 XD\n{str(e)[:200]}"
            )
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
