import os
import json
import logging

from openai import OpenAI

class ReceiptAIAgent:
    """
    This class encapsulate the logic of communicating with AI.
    Can pass API key, model, temperature as parameters.
    And provide analyze_receipt_text(ocr_text) function to analyze OCR result.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.2,
    ):
        """
        Init AI agent Object
        Will try to use Environment Variable OPENAI_API_KEY while parameter api_key is missing.
        """
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

        # System Hint:Tell AI How to respond
        self.system_prompt = (
            "你是一個專家，擅長分析收據或發票的文字內容。"
            "請根據使用者提供的文字，判斷花了多少錢（總金額），以及屬於什麼消費種類（例如：餐飲、服飾、雜貨...）。"
            "最後，請以 JSON 格式回傳，包含以下欄位：\n"
            "amount: number,\n"
            "category: string,\n"
            "confidence: number,\n"
            "original_text: string,\n"
            "請確保是合法的 JSON。"
        )

    def analyze_receipt_text(self, ocr_text: str):
        """
        Use OpenAI to analyze text after OCR, return json
        Example：
        {
          "amount": 9.50,
          "category": "餐飲",
          "confidence": 0.9,
          "original_text": "...(完整OCR內容)..."
        }
        """
        if not ocr_text.strip():
            logging.warning("OCR文字為空，無法分析。")
            return self._default_response(ocr_text)

        user_prompt = (
            f"以下是從收據或發票 OCR 得到的文字：\n{ocr_text}\n"
            "請分析並找出最可能的總金額（若有多個金額，取最可能的），"
            "消費類別（如餐飲、生活用品...），以及給我一個0~1的信心度。"
            "請回傳JSON結構: { amount, category, confidence, original_text }"
        )

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=self.temperature,
            )

            if not chat_completion.choices:
                logging.error("OpenAI 回傳的 choices 為空。")
                return self._default_response(ocr_text)

            content = chat_completion.choices[0].message.content.strip()

            # 嘗試解析JSON
            try:
                parsed_json = json.loads(content)
            except json.JSONDecodeError:
                logging.error("無法將模型回應解析為 JSON：%s", content)
                return self._default_response(ocr_text)

            # 組合結果
            result = {
                "amount": parsed_json.get("amount", None),
                "category": parsed_json.get("category", None),
                "confidence": parsed_json.get("confidence", 0),
                "original_text": parsed_json.get("original_text", ocr_text),
            }
            return result

        except Exception as e:
            logging.error("呼叫 OpenAI 過程發生錯誤：%s", e)
            return self._default_response(ocr_text)

    def _default_response(self, original_text):
        """
        Return Default json struct if call or analyze failure
        """
        return {
            "amount": None,
            "category": None,
            "confidence": 0,
            "original_text": original_text,
        }

if __name__ == "__main__":
    # Init an AI Agent Obj
    api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
    agent = ReceiptAIAgent(
        api_key=api_key,
        model="gpt-3.5-turbo",  # or "gpt-4"
        temperature=0.2
    )

    # Assume text comes from Google Vision OCR
    sample_ocr_text = """
    Starbucks Coffee
    Date: 2024-11-15
    Item: Latte Tall $4.50
    Item: Sandwich $5.00
    Total: $9.50
    Thanks for your purchase!
    """

    # Call AI Agent to analyze
    result = agent.analyze_receipt_text(sample_ocr_text)

    # Print result
    print("AI 分析結果：", result)
