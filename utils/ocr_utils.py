import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import re


def crop_image_to_roi(image):
    width, height = image.size
    upper = int(height * 0.5)  # upper y
    left = 0  # left x
    right = width  # right x
    lower = height  # bottom y
    roi_box = (left, upper, right, lower)
    cropped_image = image.crop(roi_box)
    return cropped_image

def scale_size(image):
    scale_factor = 0.7
    new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
    image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image

def preprocess_image(image):
    # Adjust Image direction
    image = ImageOps.exif_transpose(image)
    image = crop_image_to_roi(image)
    image = scale_size(image)
    # transit to grey image
    gray = image.convert('L')
    # sharpened_image = gray.filter(ImageFilter.SHARPEN)

    enhancer = ImageEnhance.Contrast(gray)
    enhanced_image = enhancer.enhance(1.2)
    # enhanced_image.save("example.png")  # Local debug use
    return enhanced_image

def extract_text_from_image(image_path, lang='chi_tra'):
    # open image
    image = Image.open(image_path)
    # preprocess image
    processed_image = preprocess_image(image)
    # OCR
    custom_config = r'--oem 3 --psm 3'
    text = pytesseract.image_to_string(processed_image, config=custom_config, lang=lang)
    text = text.replace('\n', '').strip()
    text = text.replace(' ', '').strip()
    print("OCR result:" + text)
    return text


def parse_total_amount(text):
    # replace common OCR error token
    text = text.replace('S', '$')
    text = text.replace('%', '$')

    amount_keywords = [
        '總計', '合計', '金額', '總額', '應收', '實收', '應付金額', '結算金額', '總金額',
        '总计', '合计', '金额', '总额', '应收', '实收', '应付金额', '结算金额',
        'TOTAL', 'Amount'
    ]

    # keywords
    keywords_pattern = r'(?:' + '|'.join(amount_keywords) + ')'

    # currencies
    currency_symbols = r'[￥¥$＄NT新臺幣]?'

    # digits
    amount_pattern = r'\d+[,\d]*\.?\d*'

    # construct whole regex
    pattern = keywords_pattern + r'\s*[:：]?\s*' + currency_symbols + r'\s*(' + amount_pattern + r')'

    print(f"REGEX pattern:{pattern}")

    # find all possibilities
    matches = re.findall(pattern, text)

    # go through all possibilities, check answer
    if matches:
        for match in matches:
            amount_str = match
            # remove comma
            amount = amount_str.replace(',', '')
            # valid number or not
            if amount.replace('.', '', 1).isdigit():
                return amount

    pattern_without_keyword = '(' + currency_symbols + r'\s*' + amount_pattern + r')'

    print(f"REGEX pattern:{pattern_without_keyword}")

    matches = re.findall(pattern_without_keyword, text)
    if matches:
        for amount_str in matches:
            amount = amount_str.replace(',', '')
            if amount.startswith('$'):
                amount = amount.replace('$', '', 1)
                if amount.replace('.', '', 1).isdigit():
                    return amount

    # Return error message if all regex do not match
    return "無法識別總金額"

if __name__ == "__main__":
    extract_text = extract_text_from_image("/.../xxx.JPG")
    ans = parse_total_amount(extract_text)
    print(ans)
    # conclusion: it's better to use Google Cloud Vision API to get text.
    # can't use easyocr since hardware problem: mine is Mac M3
