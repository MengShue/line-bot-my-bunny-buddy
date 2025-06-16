import os
import logging
import aiohttp
import json
from typing import Optional, List

CWA_API_BASE = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/"
CWA_API_KEY = os.environ.get("CWA_API_KEY", "YOUR_CWA_API_KEY")


async def get_cwa_product_url(dataset_id: str, product_url_path: List[str]) -> Optional[str]:
    """
    取得中央氣象局指定 dataset_id 的 ProductURL。

    Args:
        dataset_id (str): 資料集 ID（如 O-A0058-001、O-A0040-001）
        product_url_path (List[str]): 取得 ProductURL 的 JSON 路徑
    Returns:
        Optional[str]: 產品圖片網址，失敗則回傳 None
    """
    api_url = f"{CWA_API_BASE}{dataset_id}"
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, allow_redirects=False) as resp:
                if resp.status == 302:
                    location = resp.headers.get("Location")
                    if not location:
                        logging.error("CWA 302 回應缺少 Location header")
                        return None
                    async with session.get(location) as json_resp:
                        if json_resp.status != 200:
                            logging.error(f"CWA JSON 下載失敗: {json_resp.status}")
                            return None
                        try:
                            text = await json_resp.text()
                            json_data = json.loads(text)
                        except Exception as e:
                            logging.error(f"CWA JSON 解碼失敗: {e}")
                            return None
                        try:
                            data = json_data
                            for key in product_url_path:
                                data = data[key]
                            return data
                        except (KeyError, TypeError) as e:
                            logging.error(f"CWA JSON 結構異常: {e}")
                            return None
                else:
                    logging.error(f"CWA API 回應非 302: {resp.status}")
                    return None
    except Exception as e:
        logging.error(f"取得 CWA 產品圖時發生錯誤: {e}")
        return None


async def get_radar_image_url() -> Optional[str]:
    """
    取得中央氣象局雷達回波圖的 PNG 圖片網址。
    """
    # 雷達圖新版路徑
    return await get_cwa_product_url("O-A0058-001", ["cwaopendata", "dataset", "resource", "ProductURL"])


async def get_rainfall_image_url() -> Optional[str]:
    """
    取得中央氣象局雨量圖的 PNG 圖片網址。
    """
    return await get_cwa_product_url("O-A0040-001", ["cwaopendata", "dataset", "Resource", "ProductURL"])


if __name__ == "__main__":
    import asyncio
    radar_url = asyncio.run(get_radar_image_url())
    print("雷達圖：", radar_url)
    rainfall_url = asyncio.run(get_rainfall_image_url())
    print("雨量圖：", rainfall_url)