import re
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# 配置 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_uniform_invoice(ocr_text):
    """
    判斷文本是否為統一發票
    """
    condition_1 = False
    condition_2 = False
    # 判斷是否含有"電子發票"or"統一發票"
    if '電子發票' in ocr_text or '統一發票' in ocr_text:
        condition_1 = True
    # 判斷是否含有發票格式的英數字
    invoice_number_pattern = r'[A-Z]{2}[-]?\s?\d{8}'
    if re.search(invoice_number_pattern, ocr_text):
        condition_2 = True
    return condition_1 and condition_2


def process_uniform_invoice(text):
    """
    處理統一發票的邏輯，含提取號碼、期別，可否兌獎
    """
    logging.info(text)
    # 提取發票號碼
    invoice_number_pattern = r'([A-Z]{2}[-]?\s?\d{8})'
    match = re.search(invoice_number_pattern, text)
    if not match:
        return "未能提取發票號碼"
    invoice_number = match.group(1).replace(' ', '')

    # 提取發票期別
    period_info = parse_invoice_period(text)
    if not period_info:
        return "未能提取發票期別"
    year = period_info['year']
    period = period_info['period']
    month = period_info['month']
    period_str = f"{year}年第{period}期({month})"

    # 判斷是否在兌獎期間
    if not is_redeemable(period_info):
        return f"發票期別為 {period_str}，還無法兌獎或是已過兌獎期限"

    # 取得對應期別的中獎號碼
    try:
        winning_numbers = get_winning_numbers_for_period(period_info)
        if not winning_numbers:
            return f"發票期別為 {period_str}，該期中獎號碼尚未公布"
    except Exception as e:
        logging.error('獲取中獎號碼時發生錯誤：%s', e)
        return "獲取中獎號碼時發生錯誤"

    # 檢查是否中獎
    prize = check_prize(invoice_number, winning_numbers)
    logging.info(prize)
    if prize:
        return f"發票期別為 {period_str}，號碼為 {invoice_number}，恭喜中獎！獎項：{prize}"
    else:
        return f"發票期別為 {period_str}，號碼為 {invoice_number}，未中獎"


def parse_invoice_period(text):
    """
    從字串中提取發票期別，返回含年份、期別、月份的資訊
    """
    # 發票格式日期，例如"113年11-12月"
    date_pattern = r'(\d{2,3})年(\d{1,2})-(\d{1,2})月'
    match = re.search(date_pattern, text)
    if match:
        year_minguo = int(match.group(1))  # 民國年
        start_month = int(match.group(2))
        end_month = int(match.group(3))

        # 民國年轉換為公元
        year = year_minguo + 1911

        # 計算期別（1-6期）
        if start_month % 2 == 1:
            period = (start_month + 1) // 2
        else:
            period = start_month // 2

        return {'year': year, 'period': period, 'month': f"{start_month}-{end_month}月"}
    else:
        return None


def is_redeemable(period_info):
    """
    判斷發票是否在兌獎期間內
    """
    current_date = datetime.now()

    # 根據期別計算開獎日期和兌獎截止日
    draw_date, redeem_deadline = get_draw_and_redeem_dates(period_info)

    # 判斷當前日期是否在兌獎期間內
    if draw_date <= current_date <= redeem_deadline:
        return True
    else:
        return False


def get_draw_and_redeem_dates(period_info):
    """
    根據期別計算開獎日期和兌獎截止日
    """
    year = period_info['year']
    period = period_info['period']

    # 期別對應的結束月份
    end_month = period * 2
    # 開獎日期為期別結束後下一個月的25號
    draw_month = end_month + 1
    draw_year = year
    if draw_month > 12:
        draw_month -= 12
        draw_year += 1
    draw_date = datetime(draw_year, draw_month, 25)

    # 兌獎截止日是開獎後第4個月的5日
    redeem_deadline_month = draw_month + 4
    redeem_deadline_year = draw_year
    if redeem_deadline_month > 12:
        redeem_deadline_month -= 12
        redeem_deadline_year += 1
    redeem_deadline = datetime(redeem_deadline_year, redeem_deadline_month, 5)

    return draw_date, redeem_deadline


def get_winning_numbers_for_period(period_info):
    """
    根據期別，獲取對應的中獎號碼
    如果中獎號碼尚未公布，返回 None
    """
    # 獲取當前期別和上一期的訊息
    current_period_info = get_current_invoice_period()
    last_period_info = get_last_invoice_period()

    # 期別轉換為可比較字串
    def period_to_str(info):
        return f"{info['year']}-{info['period']}"

    invoice_period_str = period_to_str(period_info)
    current_period_str = period_to_str(current_period_info)
    last_period_str = period_to_str(last_period_info)

    if invoice_period_str == current_period_str:
        # 當前期別
        url = 'https://invoice.etax.nat.gov.tw/index.html'
    elif invoice_period_str == last_period_str:
        # 上期期別
        url = 'https://invoice.etax.nat.gov.tw/lastNumber.html'
    else:
        # 更早期別或更晚期別，Return None
        return None

    winning_numbers = get_winning_numbers(url)
    return winning_numbers


def get_current_invoice_period():
    """
    獲取當前期別訊息
    """
    current_date = datetime.now()
    month = current_date.month
    year = current_date.year

    # 計算期別（1-6期）
    period = (month + 1) // 2

    return {'year': year, 'period': period}


def get_last_invoice_period():
    """
    獲取上一期期別訊息
    """
    current_date = datetime.now()
    month = current_date.month
    year = current_date.year

    # 計算期別（1-6期）
    period = (month + 1) // 2

    # 如果是第一期，上一期是上一年的第六期
    if period == 1:
        last_period = 6
        last_year = year - 1
    else:
        last_period = period - 1
        last_year = year

    return {'year': last_year, 'period': last_period}


def get_winning_numbers(url):
    """
    從財政部稅務入口網獲取最新中獎號碼及規則
    """
    response = requests.get(url)
    response.encoding = 'utf-8'  # utf-8

    if response.status_code != 200:
        raise Exception('無法獲取最新中獎號碼頁面')

    soup = BeautifulSoup(response.text, 'lxml')

    # 提取期别
    title = soup.find('a', href="lastNumber.html").get_text(strip=True)
    period_match = re.search(r'(\d+)年(\d+)-(\d+)月', title)
    if not period_match:
        raise Exception('無法解析期別')
    year = int(period_match.group(1)) + 1911  # 民國轉公元
    months = period_match.group(2) + '-' + period_match.group(3)

    # 提取中獎號碼
    winning_numbers = {
        'special_prize': [],  # 特別獎 (1000萬元)
        'grand_prize': [],  # 特獎 (200萬元)
        'first_prize': [],  # 頭獎 (20萬元)
        'additional_sixth_prize': []  # 增開六獎 (200元)
    }

    # 特別獎
    special_prize = soup.find_all('span', {'class': 'font-weight-bold etw-color-red'})
    if special_prize:
        winning_numbers['special_prize'].append(special_prize[0].get_text(strip=True))

    # 特獎
    if special_prize:
        winning_numbers['grand_prize'].append(special_prize[1].get_text(strip=True))


    # 頭獎
    first_prize = soup.find_all('span', {'class': 'font-weight-bold'})
    if first_prize:
        for i in range(2,8,2):
            first_prize_numbers = first_prize[i].get_text(strip=True) + first_prize[i + 1].get_text(strip=True)
            winning_numbers['first_prize'].append(first_prize_numbers)

    # 增開六獎
    additional_sixth_prize = first_prize
    if additional_sixth_prize:
        for i in range(2, 8, 2):
            additional_sixth_prize_numbers = first_prize[i + 1].get_text(strip=True)
            winning_numbers['additional_sixth_prize'].append(additional_sixth_prize_numbers)

    logging.info(f"從財政部稅務入口網獲取最新中獎號碼:{winning_numbers}")

    return winning_numbers


def check_prize(invoice_number, winning_numbers):
    """
    根據中獎號碼，檢查是否中獎，返回中獎獎項
    """
    invoice_num = invoice_number[-8:]  # 發票號碼後8位數字部分

    # 檢查特別獎
    for num in winning_numbers['special_prize']:
        if invoice_num == num:
            return '特別獎 1,000萬元'

    # 檢查特獎
    for num in winning_numbers['grand_prize']:
        if invoice_num == num:
            return '特獎 200萬元'

    # 檢查頭獎及相關獎項
    for num in winning_numbers['first_prize']:
        prize_level = match_first_prize(invoice_num, num)
        if prize_level:
            return prize_level

    # 檢查增開六獎
    for num in winning_numbers['additional_sixth_prize']:
        if invoice_num[-3:] == num:
            return '增開六獎 200元'

    return None


def match_first_prize(invoice_num, winning_num):
    """
    檢查發票號碼與頭獎號碼，確認中獎等級
    """
    prize_names = {
        8: '頭獎 20萬元',
        7: '二獎 4萬元',
        6: '三獎 1萬元',
        5: '四獎 4千元',
        4: '五獎 1千元',
        3: '六獎 200元',
    }
    for i in range(8, 2, -1):
        if invoice_num[-i:] == winning_num[-i:]:
            return prize_names[i]
    return None

# local debug use
if __name__ == "__main__":
    image_path = '/.../XXX.JPG'
    from utils.ocr_cloudvision import extract_text_from_image
    test_text = extract_text_from_image(image_path)
    print(test_text)
    # text = '113年11-12月  HM-97282721'
    result = ''
    if is_uniform_invoice(test_text):
        # 處理發票邏輯
        result = process_uniform_invoice(test_text)
    print(result)