import os
import yaml
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 从环境变量中获取 LINE Channel Secret 和 Access Token
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建 config.yaml 的路径（根目录）
config_path = os.path.join(current_dir, '..', 'config.yaml')

# 读取 YAML 配置文件
with open(config_path, 'r') as yml:
    config = yaml.safe_load(yml)

# 从配置文件中获取主机和端口
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
def handle_message(event):
    # 回复相同的消息
    reply_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # 检查是否在 Heroku 环境中
    if 'PORT' in os.environ:
        port = int(os.environ.get('PORT', PORT))
        host = '0.0.0.0'
    else:
        port = PORT
        host = HOST
    app.run(host=host, port=port)