import requests
import yaml
import os

# 讀取 config 檔案取得 server ip/port
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'integration_config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

HOST = config.get('host', '127.0.0.1')
PORT = config.get('port', 5500)


def test_callback_missing_signature():
    """
    測試 /callback API 當缺少 X-Line-Signature header 時，應回傳 500（目前 app.py 未處理 header 缺失）。
    """
    url = f"http://{HOST}:{PORT}/callback"
    payload = {
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "text": "@雷達"},
                "source": {"userId": "U1234567890"}
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=5)
    assert resp.status_code == 500
