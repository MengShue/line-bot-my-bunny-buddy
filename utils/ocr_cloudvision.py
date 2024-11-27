from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import vision
from google.oauth2 import service_account
from itertools import groupby
import logging
import json
import os
import io
import re


# Logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


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
    # print(text)  # local debug use
    # text to string list
    lines = text.strip().split('\n')
    lines = [ x
              for item in lines
              for x in item.split(':')
              ]
    lines = [x
             for item in lines
             for x in item.split(' ')
             ]
    # split digits and alphabetic string
    lines = [''.join(j).strip()
             for item in lines
             for k, j in groupby(item, str.isdigit)
             ]
    logging.info(f"google vision api return string:{lines}")

    # List of currency total amount definition
    amount_keywords = [
        '銷售總額', '總計', '總額', '應收', '應付金額', '結算金額', '總金額',
        '销售总额', '总计', '总额', '应收', '应付金额', '结算金额', '总金额',
        'Grand Total', 'TOTAL', 'Payable', '合計', '金额', '金額'
    ]

    # Record every amount after keyword showing
    amounts_after_keywords = []

    # Traverse from beginning
    for i in range(len(lines)):
        line = lines[i].strip()
        # Detect if containing keyword
        for keyword in amount_keywords:
            if keyword in line:
                # Find number in the following list
                amounts_found = []
                for j in range(1, 6):  # check al least 5 elements
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        # Find all digits
                        numbers = re.findall(r'\d+[,\d]*\.?\d*', next_line.replace(',', ''))
                        for num_str in numbers:
                            try:
                                amount_value = float(num_str.replace(',', ''))
                                amounts_found.append(amount_value)
                            except ValueError:
                                continue
                if amounts_found:
                    # Record the maximum digits and its index after keyword
                    max_amount = max(amounts_found)
                    amounts_after_keywords.append((i, max_amount))
                break  # No need to find another keyword after find one

    if amounts_after_keywords:
        # Select the last keyword and maximum number
        last_index, last_amount = amounts_after_keywords[-1]
        return str(last_amount)

    # Return error string if you can not find
    return "無法識別總金額"

def extract_text_from_image(image_path):
    text = detect_text(image_path)
    return text

# Local use
if __name__ == "__main__":
    image_path = '.../xxx.JPG'
    text = extract_text_from_image(image_path)
    amount = parse_total_amount(text)
    print(f"提取的金额：{amount}")