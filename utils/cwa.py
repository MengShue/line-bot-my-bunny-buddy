import os
import logging
import aiohttp
import json
from typing import Optional

CWA_API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0058-001"
CWA_API_KEY = os.environ.get("CWA_API_KEY", "YOUR_CWA_API_KEY")

async def get_radar_image_url() -> Optional[str]:
    """
    取得中央氣象局雷達回波圖的 PNG 圖片網址。

    Returns:
        Optional[str]: 雷達回波圖的 PNG 圖片網址，若失敗則回傳 None。
    """
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CWA_API_URL, params=params, allow_redirects=False) as resp:
                print(resp.status)
                print(resp.headers)
                print(resp.text)
                if resp.status == 302:
                    location = resp.headers.get("Location")
                    if not location:
                        logging.error("CWA 302 回應缺少 Location header")
                        return None
                    # 取得 JSON 內容
                    async with session.get(location) as json_resp:
                        if json_resp.status != 200:
                            logging.error(f"CWA JSON 下載失敗: {json_resp.status}")
                            return None
                        # 強制用 text 讀取再 json.loads，避免 Content-Type 問題
                        try:
                            text = await json_resp.text()
                            json_data = json.loads(text)
                        except Exception as e:
                            logging.error(f"CWA JSON 解碼失敗: {e}")
                            return None
                        try:
                            return json_data["cwaopendata"]["dataset"]["resource"]["ProductURL"]
                        except (KeyError, TypeError) as e:
                            logging.error(f"CWA JSON 結構異常: {e}")
                            return None
                else:
                    logging.error(f"CWA API 回應非 302: {resp.status}")
                    return None
    except Exception as e:
        logging.error(f"取得 CWA 雷達回波圖時發生錯誤: {e}")
        return None 
    
if __name__ == "__main__":
    import asyncio
    url = asyncio.run(get_radar_image_url())
    print(url)