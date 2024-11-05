import os
import yaml
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageMessage
# OCR module
from utils.ocr_utils import extract_text_from_image, parse_total_amount


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
    app.logger.info(f"Get Message: {event.message}")
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
    text = extract_text_from_image(temp_file_path, lang='chi_tra+eng')

    # Get Total amount
    total_amount = parse_total_amount(text)

    # Reply total amount
    reply_text = f"總計花費：{total_amount}元"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # Detect if it is in Heroku
    if 'PORT' in os.environ:
        port = int(os.environ.get('PORT', PORT))
        host = '0.0.0.0'
    else:
        port = PORT
        host = HOST
    app.run(host=host, port=port)
