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
MODEL_NAME = "gpt-5.5"

SEARCH_KEYWORDS = [
    "最新",
    "今天",
    "新聞",
    "股價",
    "賽程",
    "比分",
    "戰況",
    "分組",
    "NBA",
    "MLB",
    "NHL",
    "足球",
    "棒球",
    "籃球",
    "馬刺",
    "尼克",
    "湖人",
    "勇士",
    "演唱會",
    "售票",
    "門票",
    "天氣",
    "發售"
]
chat_memory = defaultdict(list)

SYSTEM_PROMPT = """
回答請使用繁體中文。

你是一位台灣網友。

聊天風格：
- 像 Threads 網友
- 像 Dcard 留言區
- 像 PTT 鄉民閒聊
- 自然口語
- 不要太正式
- 可以有自己的觀點
- 像朋友聊天

口頭禪：
- 偶爾自然使用「確實」
- 遇到衝動、誇張或成人話題時，可以說「冷靜」
- 遇到離譜事情時，可以說「法克」
- 不要刻意使用
- 不要每句都出現

回答風格：
- 像 LINE 訊息
- 少用條列
- 少用表格
- 少用 Markdown
- 不要使用 **
- 不要使用 ###

網路搜尋規則：

如果使用網路搜尋：

- 直接回答問題
- 直接給結果
- 不要反問
- 不要要求補資料
- 不要要求貼圖片
- 不要要求貼網址
- 不要提到搜尋過程
- 不要貼來源網址
- 不要貼引用

若資訊不足：

- 直接說查不到可靠資料

不要進入反覆確認模式。

當使用者詢問：
- 分組
- 名單
- 排名
- 賽程
- 比分
- 股價
- 演唱會資訊
- 售票資訊

請優先直接給答案。

不要只說：
「有結果」
「有分組」
「有名單」

必須直接說明內容。

不要自稱 AI。
不要使用簡體中文。

"""
SEARCH_KEYWORDS = [
    "最新",
    "今天",
    "新聞",
    "股價",
    "賽程",
    "比分",
    "戰況",
    "分組",
    "NBA",
    "MLB",
    "NHL",
    "足球",
    "棒球",
    "籃球",
    "馬刺",
    "尼克",
    "湖人",
    "勇士",
    "演唱會",
    "售票",
    "門票",
    "天氣",
    "發售"
]
SPORT_KEYWORDS = [
    "NBA",
    "MLB",
    "馬刺",
    "尼克",
    "湖人",
    "勇士",
    "戰況",
    "比分",
    "賽程"
]
@app.route("/")
def home():
    return f"{MODEL_NAME} Bot Running"

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
                text="重製成功 !!"
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
            模型：{MODEL_NAME}

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
                model={MODEL_NAME},
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
    chat_memory[room_id] = chat_memory[room_id][-20:]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(chat_memory[room_id])
    is_sport = any(
        word.lower() in user_text.lower()
        for word in SPORT_KEYWORDS
    )

    if is_sport:
        messages.append(
        {
            "role": "system",
            "content": """
你是專業體育記者。

若今天沒有比賽：

1. 查詢最近一場比賽結果
2. 查詢下一場比賽時間
3. 說明系列賽狀況
4. 不要只回答 No games found
5. 不要直接說查不到
6. 使用繁體中文
"""
        }
    )
    try:
        need_search = any(
        word in user_text
        for word in SEARCH_KEYWORDS
        )
        print(f"need_search = {need_search}")
        print(f"user_text = {user_text}")
        if need_search:
            response = client.responses.create(
                model="gpt-5.4-mini",
                tools=[
                    {
                    "type": "web_search"
                    }
                ],
            input=messages
            )
            print(f"MODEL = {MODEL_NAME}")
            print(f"SEARCH = {need_search}")
            print(f"SPORT = {is_sport}")
            print(f"QUESTION = {user_text}")
            print("=" * 50)
        else:

            response = client.responses.create(
            model="gpt-5.4-mini",
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
    
