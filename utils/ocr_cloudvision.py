from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import vision
from google.oauth2 import service_account
from itertools import groupby
from datetime import datetime
import logging
import json
import os
import io
import re


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

def parse_total_amount(text, lines_to_check=5):
    # print(text)  # local debug use
    # text to string list
    lines = text.strip().split('\n')
    lines = [ x
              for item in lines
              for x in item.split(':')
              ]
    lines = [ item for item in lines if item != '']

    # List of currency total amount definition
    amount_keywords = [
        '銷售總額', '總計', '總額', '應收', '應付金額', '結算金額', '總金額',
        '销售总额', '总计', '总额', '应收', '应付金额', '结算金额', '总金额',
        'Grand Total', 'TOTAL', 'Payable', '合計', '金额', '金額'
    ]
    logging.info(f"line:\n {lines}")
    try:

        # Record possible amount candidate
        candidate_amounts = []

        # Traverse from beginning
        for i, line in enumerate(lines):
            line = line.strip()
            # Detect if containing keyword
            for keyword in amount_keywords:
                if keyword in line:
                    # Find number in the following list
                    start_index = max(0, i - lines_to_check)
                    end_index = min(len(lines), i + lines_to_check + 1)
                    possible_amounts = []
                    for j in range(start_index, end_index):
                        amounts_in_line = extract_amounts_from_line(lines[j])
                        possible_amounts.extend(amounts_in_line)

                    # Filter possible amount
                    filtered_amounts = filter_possible_amounts(possible_amounts)

                    # If found filtered amount, add to candidate
                    if filtered_amounts:
                        candidate_amounts.extend(filtered_amounts)
                    break  # No need to find another keyword after find one

        if candidate_amounts:
            # Return the maximum digits
            total_amount = max(candidate_amounts)
            return str(total_amount)

        # Return can't find if we can't recognize
        return "無法識別總金額"
    except Exception as e:
        logging.error('解析金額時發生錯誤：%s', e)
        return "無法識別總金額"


def extract_amounts_from_line(line):
    """
    從字串中提取可能金額列表
    """
    # 移除漢字和單位
    line = re.sub(r'[元圓圆]', '', line)

    # 提取含數字和逗點、小數點、貨幣符號的字串
    amount_patterns = re.findall(r'[\$￥]?[\d,]+\.?\d*', line)
    amounts = []
    for amt_str in amount_patterns:
        # 移除貨幣符號
        amt_str = amt_str.replace('$', '').replace('￥', '')
        amt_str = amt_str.replace(',', '')  # 移除逗號
        try:
            amount_value = float(amt_str)
            amounts.append(amount_value)
        except ValueError:
            continue
    return amounts


def filter_possible_amounts(amounts):
    """
    過濾可能的金額，排除年份、日期等不太可能是金額的數字。
    """
    filtered_amounts = []
    current_date = datetime.now()
    year = current_date.year
    for amt in amounts:
        # 排除年份
        if amt == year:
            continue  # 可能是年份，排除
        if amt == 0:
            continue  # 排除為0的金額
        if amt > 1000000:
            continue  # 排除過大的金額
        # 可以新增排除條件
        filtered_amounts.append(amt)
    return filtered_amounts

def extract_text_from_image(image_path):
    text = detect_text(image_path)
    return text

# Local use
if __name__ == "__main__":
    image_path = '.../xxx.JPG'
    text = extract_text_from_image(image_path)
    print(f"\n{text}")
    amount = parse_total_amount(text)
    print(f"\n提取的金额：{amount}")