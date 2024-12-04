import os
import yaml
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageMessage
# OCR module
from utils.ocr_cloudvision import extract_text_from_image, parse_total_amount
from utils.invoice_processing import is_uniform_invoice, process_uniform_invoice
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

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    # reply_text = event.message.text
    logging.info(f"Get Message: {event.message}")
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

    # Get Message
    kind, message = process_receipt_or_invoice(text)

    # Reply Message
    if kind == 'invoice':
        reply_text = f"""
        \u2764 看起來是一張收據喔 \u2764
        支出已追蹤：{message}
        """
    elif kind == 'receipt':
        reply_text = f"""
        \u2764 看起來是一張發票喔 \u2764
        試圖幫你兌獎：{message}
        """
    else:
        reply_text = f"""
        \u2764 你餵我吃了什麼？ \u2764
        我只吃發票或收據喔!
        """
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
