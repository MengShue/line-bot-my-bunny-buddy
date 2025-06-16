import os
from dotenv import load_dotenv
import yaml
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage

# OCR module
from utils.ocr_cloudvision import extract_text_from_image, parse_total_amount
from utils.invoice_processing import is_uniform_invoice, process_uniform_invoice
from utils.cwa import get_radar_image_url, get_rainfall_image_url
# Logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Get LINE Channel Secret and Access Token from Environment Variables
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Get directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get directory of YAML file
config_path = os.path.join(current_dir, '..', 'config.yaml')

# Read YAML
with open(config_path, 'r') as yml:
    config = yaml.safe_load(yml)

# Get host and port
HOST = config['server']['host']
PORT = config['server']['port']

load_dotenv()


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 新增：嘗試解析 userId 與 text 並 logging
    try:
        import json
        json_data = json.loads(body)
        events = json_data.get('events', [])
        if events:
            event = events[0]
            user_id = event.get('source', {}).get('userId', None)
            text = event.get('message', {}).get('text', None)
            logging.info(f"LINE Request - userId: {user_id}, text: {text}")
    except Exception as e:
        logging.warning(f"解析 userId/text 失敗: {e}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text.strip()
    if user_text == "@雷達":
        import asyncio
        try:
            radar_url = asyncio.run(get_radar_image_url())
            if radar_url:
                line_bot_api.reply_message(
                    event.reply_token,
                    ImageSendMessage(original_content_url=radar_url, preview_image_url=radar_url)
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="⚡ 取得雷達回波圖失敗，請稍後再試。")
                )
        except Exception as e:
            logging.error(f"取得雷達回波圖時發生錯誤: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚡ 取得雷達回波圖時發生錯誤，請稍後再試。")
            )
        return
    if user_text == "@雨量":
        import asyncio
        try:
            rainfall_url = asyncio.run(get_rainfall_image_url())
            if rainfall_url:
                line_bot_api.reply_message(
                    event.reply_token,
                    ImageSendMessage(original_content_url=rainfall_url, preview_image_url=rainfall_url)
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="⚡ 取得雨量圖失敗，請稍後再試。")
                )
        except Exception as e:
            logging.error(f"取得雨量圖時發生錯誤: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚡ 取得雨量圖時發生錯誤，請稍後再試。")
            )
        return
    # 其他文字訊息暫不處理
    print(f"Get Message: {event.message}")
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(text=reply_text)
    # )


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # Handle image
    handle_image_message(event)


def handle_image_message(event):
    # Download image from line
    message_content = line_bot_api.get_message_content(event.message.id)
    temp_file_path = f"{event.message.id}.jpg"

    with open(temp_file_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    # Use OCR
    text = extract_text_from_image(temp_file_path)

    print(f"OCR result:{text}")

    # Get Message
    kind, message = process_receipt_or_invoice(text)
    print(f"kind: {kind}")
    print(f"message: {message}")

    # Reply Message
    if kind == 'receipt' and type(message) is dict:
        amount = message["amount"]
        category = message["category"]
        reply_text = f"\u2764 看起來是一張收據喔 \u2764\n支出已追蹤：{amount}\n消費類別：{category}"
    elif kind == 'invoice':
        reply_text = f"\u2764 看起來是一張發票喔 \u2764\n試圖幫你兌獎：{message}"
    elif kind == 'receipt' and type(message) is str:
        reply_text = "\u2764 看起來是一張收據喔 \u2764\n但分析時出了些問題QQ"
    else:
        reply_text = "\u2764 你餵我吃了什麼？ \u2764\n我只吃發票或收據喔!"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
    os.remove(temp_file_path)


def process_receipt_or_invoice(text):
    if is_uniform_invoice(text):
        # 發票，處理發票邏輯
        result = process_uniform_invoice(text)
        return 'invoice', result
    else:
        # 收據，處理收據邏輯
        amount = parse_total_amount(text)
        return 'receipt', amount


if __name__ == "__main__":
    # Detect if it is in Heroku
    if 'PORT' in os.environ:
        port = int(os.environ.get('PORT', PORT))
        host = '0.0.0.0'
    else:
        port = PORT
        host = HOST
    app.run(host=host, port=port)
