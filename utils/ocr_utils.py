import os

import pytesseract
from PIL import Image
import re

def preprocess_image(image):
    # transit to grey image
    gray = image.convert('L')
    # 二值化處理
    threshold = 200
    binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
    return binary

def extract_text_from_image(image_path, lang='chi_tra'):
    # open image
    image = Image.open(image_path)
    # preprocess image
    # processed_image = preprocess_image(image)
    # OCR
    text = pytesseract.image_to_string(image, lang=lang)
    print("OCR result:" + text)
    return text

def parse_total_amount(text):
    # REGEX to get total amount
    pattern = r'(总计|合计|金额|TOTAL|總計|合計|金額)\s*[:：]?\s*[￥¥$NT新臺幣]?\s*(\d+[,\d]*\.?\d*)[元]?'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        # get last matched group
        amount = matches[-1][1]
        # delete possible comma
        amount = amount.replace(',', '')
        return amount
    else:
        return "無法識別總金額"