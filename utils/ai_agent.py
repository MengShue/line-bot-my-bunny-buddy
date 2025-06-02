import os
import json
import logging
from typing import Optional, Any, Dict

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from openai import OpenAI

class ReceiptAIAgent:
    """
    This class encapsulate the logic of communicating with AI.
    Can pass API key, model, temperature as parameters.
    And provide analyze_receipt_text(ocr_text) function to analyze OCR result.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.2,
        provider: str = "openai",
    ):
        """
        Init AI agent Object
        Will try to use Environment Variable OPENAI_API_KEY or GEMINI_API_KEY while parameter api_key is missing.
        provider: 'openai' or 'gemini'
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.api_key = api_key

        if self.provider == "gemini":
            if api_key is None:
                api_key = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
            if genai is None:
                raise ImportError("google-generativeai 未安裝，請先安裝 google-generativeai 套件。")
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        elif self.provider == "openai":
            if api_key is None:
                api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"不支援的 AI provider: {self.provider}")

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

    def analyze_receipt_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Use AI to analyze text after OCR, return json
        """
        if not ocr_text.strip():
            logging.warning("OCR文字為空，無法分析。")
            return self._default_response(ocr_text)

        user_prompt = (
            f"以下是從收據或發票 OCR 得到的文字：\n{ocr_text}\n"
            "請分析並找出最可能的總金額（若有多個金額，取最可能的），"
            "消費類別（如餐飲、生活用品...），以及給我一個0~1的信心度。"
            "請回傳JSON字串(務必合法json，```之後不需有json這四個英文字): { amount, category, confidence, original_text }"
        )

        try:
            if self.provider == "openai":
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
            elif self.provider == "gemini":
                response = self.gemini_model.generate_content([
                    {"role": "user", "parts": [self.system_prompt + "\n" + user_prompt]}
                ])
                content = response.text.strip()
                # 處理 Gemini 可能回傳的 ```json ... ``` 或 ``` ... ``` 區塊
                if content.startswith("```json"):
                    content = content.removeprefix("```json").strip()
                if content.startswith("```"):
                    content = content.removeprefix("```").strip()
                if content.endswith("```"):
                    content = content.removesuffix("```").strip()
            else:
                raise ValueError(f"不支援的 AI provider: {self.provider}")

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
            logging.error(f"呼叫 {self.provider} 過程發生錯誤：%s", e)
            return self._default_response(ocr_text)

    def _default_response(self, original_text: str) -> Dict[str, Any]:
        """
        Return Default json struct if call or analyze failure
        """
        return {
            "amount": None,
            "category": None,
            "confidence": 0,
            "original_text": original_text,
        }

# 工廠函式：根據環境變數自動選擇 AI provider
def get_receipt_ai_agent_from_env() -> ReceiptAIAgent:
    """
    根據環境變數 AI_PROVIDER (預設 gemini) 自動建立 ReceiptAIAgent
    """
    provider = os.environ.get("AI_PROVIDER", "gemini").lower()
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", None)
        return ReceiptAIAgent(api_key=api_key, provider="gemini")
    else:
        api_key = os.environ.get("OPENAI_API_KEY", None)
        return ReceiptAIAgent(api_key=api_key, provider="openai")

if __name__ == "__main__":
    # Init an AI Agent Obj
    agent = get_receipt_ai_agent_from_env()

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
