from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import vision
from google.oauth2 import service_account
import logging
import json
import os
import io
from utils.ai_agent import get_receipt_ai_agent_from_env

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_vision_client():
    try:
        # Detect Environment
        if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' not in os.environ:
            raise EnvironmentError('Environment variable GOOGLE_APPLICATION_CREDENTIALS_JSON Not yet setting')
        # Load service info
        service_account_info = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        return client
    except json.JSONDecodeError as e:
        logging.error('Service account JSON Analyze error：%s', e)
        raise
    except Exception as e:
        logging.error('Init Vision API client error：%s', e)
        raise

def detect_text(path):
    client = get_vision_client()

    try:
        with io.open(path, 'rb') as image_file:
            content = image_file.read()
    except FileNotFoundError:
        logging.error('File Not Found:%s', path)
        return ''
    except Exception as e:
        logging.error('Error while reading:%s', e)
        return ''

    try:
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        if response.error.message:
            logging.error('Vision API return error：%s', response.error.message)
            return ''
        texts = response.text_annotations
        if texts:
            return texts[0].description
        else:
            logging.warning('Can not detect any text.')
            return ''
    except GoogleAPICallError as e:
        logging.error('Call Vision API error:%s', e)
        return ''
    except RetryError as e:
        logging.error('Call Vision API Retry error:%s', e)
        return ''
    except Exception as e:
        logging.error('Handle Vision API Response error:%s', e)
        return ''

def parse_total_amount(text):
    try:
        agent = get_receipt_ai_agent_from_env()
        result = agent.analyze_receipt_text(text)
        return result
    except Exception as e:
        logging.error('解析金額時發生錯誤：%s', e)
        return "無法識別總金額"

def extract_text_from_image(image_path):
    text = detect_text(image_path)
    return text

# Local use
if __name__ == "__main__":
    image_path = '.../xxx.JPG'
    text = extract_text_from_image(image_path)
    print(f"\n{text}")
    message = parse_total_amount(text)
    print(f"AI return message: {message}\n")
    amount = message["amount"]
    category = message["category"]
    reply_text = f"提取的金额：{amount}\n消費類別：{category}"
    print(f"\n{reply_text}")