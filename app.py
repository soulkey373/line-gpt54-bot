from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
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

    user_text = event.message.text

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=user_text
    )

    reply_text = response.output_text

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text[:5000])
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)