import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import re


def preprocess_image(image):
    # Adjust Image direction
    image = ImageOps.exif_transpose(image)
    # transit to grey image
    gray = image.convert('L')
    sharpened_image = gray.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(sharpened_image)
    enhanced_image = enhancer.enhance(2.0)
    # enhanced_image.save("example.png")  # Local debug use
    return enhanced_image

def extract_text_from_image(image_path, lang='chi_tra'):
    # open image
    image = Image.open(image_path)
    # preprocess image
    processed_image = preprocess_image(image)
    # OCR
    text = pytesseract.image_to_string(processed_image, lang=lang)
    text = text.replace('\n', '').strip()
    text = text.replace(' ', '').strip()
    print("OCR result:" + text)
    return text

def parse_total_amount(text):
    # First REGEX match
    pattern1 = r'(总计|合计|金额|TOTAL|總計|合計|金額)\s*[:：]?\s*[￥¥$＄NT新臺幣]?\s*(\d+[,\d]*\.?\d*)'
    matches = re.findall(pattern1, text, re.IGNORECASE)
    if matches:
        amount = matches[-1][1].replace(',', '')
        return amount
    else:
        # Second REGEX match, considering replacing general OCR error
        text_corrected = text.replace('S', '$').replace('%', '$')
        pattern2 = r'(总计|合计|金额|TOTAL|總計|合計|金額)\s*[:：]?\s*[￥¥$＄NT新臺幣$]?\s*(\d+[,\d]*\.?\d*)'
        matches = re.findall(pattern2, text_corrected, re.IGNORECASE)
        if matches:
            amount = matches[-1][1].replace(',', '')
            return amount
        else:
            # Try to match number again
            text_corrected = text.replace('S', '$').replace('%', '$').replace('NT', '$')
            pattern3 = r'[￥¥$＄S%]{1}\s*(\d+[,\d]*\.?\d*)'
            matches = re.findall(pattern3, text_corrected)
            if matches:
                amount = matches[-1].replace(',', '')
                return amount
            else:
                return "無法識別總金額"

if __name__ == "__main__":
    extract_text = extract_text_from_image("/.../xxx.JPG")
    ans = parse_total_amount(extract_text)
    print(ans)
