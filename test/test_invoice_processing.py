from utils.invoice_processing import (
    parse_invoice_period,
    is_redeemable,
    get_draw_and_redeem_dates,
    check_prize,
    match_first_prize,
    process_uniform_invoice,
    get_current_invoice_period,
    get_last_invoice_period,
)

import unittest
from unittest.mock import patch
from datetime import datetime
import os
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [unittest]- %(levelname)s - %(message)s', stream=sys.stdout)
# 獲取程式根目錄
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 將跟目錄加到 sys.path
sys.path.insert(0, parent_dir)


class TestInvoiceProcessing(unittest.TestCase):


    def test_parse_invoice_period(self):
        # Normal
        text = "中華民國113年11-12月份收銀機統一發票DY21294127"
        period_info = parse_invoice_period(text)
        self.assertIsNotNone(period_info)
        self.assertEqual(period_info['year'], 2024)
        self.assertEqual(period_info['period'], 6)

        # Different format
        text = "中華民國 113年11-12月份 收銀機統一發票DY21294127"
        period_info = parse_invoice_period(text)
        self.assertIsNotNone(period_info)
        self.assertEqual(period_info['year'], 2024)
        self.assertEqual(period_info['period'], 6)

        # Wrong format
        text = "統一發票：113年 11-12月"
        period_info = parse_invoice_period(text)
        self.assertIsNone(period_info)


    def test_is_redeemable(self):
        # 現在期別
        period_info = get_current_invoice_period()
        redeemable = is_redeemable(period_info)
        # 根據日期，可能為 True 或 False，這裡不做判斷

        # 過去的期別（已過兌獎期限）
        past_period_info = {'year': 2022, 'period': 1}
        redeemable = is_redeemable(past_period_info)
        self.assertFalse(redeemable)

        # 未來的期別（尚未開獎）
        future_period_info = {'year': datetime.now().year + 1, 'period': 1}
        redeemable = is_redeemable(future_period_info)
        self.assertFalse(redeemable)


    def test_get_draw_and_redeem_dates(self):
        # 測試第6期(11-12月)
        period_info = {'year': 2024, 'period': 6}
        draw_date, redeem_deadline = get_draw_and_redeem_dates(period_info)
        self.assertEqual(draw_date, datetime(2025, 1, 25))
        self.assertEqual(redeem_deadline, datetime(2025, 5, 5))


    def test_match_first_prize(self):
        invoice_num = '12345678'
        winning_num = '12345678'
        prize = match_first_prize(invoice_num, winning_num)
        self.assertEqual(prize, '頭獎 20萬元')

        invoice_num = '22345678'
        prize = match_first_prize(invoice_num, winning_num)
        self.assertEqual(prize, '二獎 4萬元')

        invoice_num = '01345678'
        prize = match_first_prize(invoice_num, winning_num)
        self.assertEqual(prize, '三獎 1萬元')

        invoice_num = '00321678'
        prize = match_first_prize(invoice_num, winning_num)
        self.assertEqual(prize, '六獎 200元')


    @patch('utils.invoice_processing.get_winning_numbers')
    def test_check_prize(self, mock_get_winning_numbers):
        # mock 中獎號碼
        winning_numbers = {
            'special_prize': ['12345678'],
            'grand_prize': ['23456789'],
            'first_prize': ['34567890', '45678901'],
            'additional_sixth_prize': ['890']
        }
        mock_get_winning_numbers.return_value = winning_numbers

        # 測試特別獎
        invoice_number = 'AB12345678'
        prize = check_prize(invoice_number, winning_numbers)
        self.assertEqual(prize, '特別獎 1,000萬元')

        # 測試增開六獎
        invoice_number = 'AB12345890'
        prize = check_prize(invoice_number, winning_numbers)
        self.assertEqual(prize, '六獎 200元')

        # 測試未中獎
        invoice_number = 'AB00000000'
        prize = check_prize(invoice_number, winning_numbers)
        self.assertIsNone(prize)


    @patch('utils.invoice_processing.get_winning_numbers_for_period')
    @patch('utils.invoice_processing.parse_invoice_period')
    def test_process_uniform_invoice(self, mock_parse_invoice_period, mock_get_winning_numbers_for_period):
        # mock 發票期別
        period_info = get_last_invoice_period()
        period_info['month'] = f"{period_info['period'] * 2 - 1}-{period_info['period'] * 2}月"
        mock_parse_invoice_period.return_value = period_info

        # mock 中獎號碼
        winning_numbers = {
            'special_prize': ['12345678'],
            'grand_prize': ['23456789'],
            'first_prize': ['34567890', '45678901'],
            'additional_sixth_prize': ['890']
        }
        mock_get_winning_numbers_for_period.return_value = winning_numbers

        # 測試中獎狀況
        text = f"中華民國{period_info['year'] - 1911}年{period_info['month']}份\n收銀機統一發票\nAB12345678"
        logging.info(f"測試發票:{text}")
        result = process_uniform_invoice(text)
        self.assertIn("恭喜中獎", result)

        # 測試未中獎情形
        text = f"中華民國{period_info['year'] - 1911}年{period_info['month']}份\n收銀機統一發票\nAB87654321"
        logging.info(f"測試發票:{text}")
        result = process_uniform_invoice(text)
        self.assertIn("未中獎", result)

        # 測試未能提取發票號碼
        text = "中華民國112年11-12月份\n"
        result = process_uniform_invoice(text)
        self.assertIn("未能提取發票號碼", result)

        # 測試未能提取發票期別
        mock_parse_invoice_period.return_value = None
        text = "收銀機統一發票\nAB12345678\n"
        result = process_uniform_invoice(text)
        self.assertIn("未能提取發票期別", result)


    def test_get_current_and_last_period(self):
        current_period = get_current_invoice_period()
        last_period = get_last_invoice_period()
        # 檢查期別合理性
        self.assertIn(current_period['period'], [1, 2, 3, 4, 5, 6])
        self.assertIn(last_period['period'], [1, 2, 3, 4, 5, 6])
        # 檢查年份合理性
        self.assertGreaterEqual(current_period['year'], 2023)
        self.assertGreaterEqual(last_period['year'], 2022)


if __name__ == '__main__':
    unittest.main()
