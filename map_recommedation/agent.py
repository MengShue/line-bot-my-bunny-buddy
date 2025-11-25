import logging
import os
import asyncio

from dotenv import load_dotenv
from google.genai import types
from google.adk.models.google_llm import Gemini

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

# MCP 連線元件
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()  # Load .env
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
logging.info(GOOGLE_MAPS_API_KEY)



# retry config
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# === Create McpToolset: Start Google Maps MCP server with npx and pass API key ===
maps_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-google-maps",
            ],
            env={
                "GOOGLE_MAPS_API_KEY": GOOGLE_MAPS_API_KEY or ""
            },
        ),
        timeout=60.0,
    ),
    # Can also use tool_filter to limit tool list (e.g. only keep nearby / details / geocode)
)

# === Create Agent instruction (system prompt)===
SYSTEM_INSTRUCTION = """
你是一位在地美食嚮導。流程：
1) 先將使用者給的地點（或預設「新北市板橋」）地理編碼成經緯度。
2) 搜尋 2 公里內的「咖啡廳」與「餐廳」各 8 家做為候選。
3) 對每個候選呼叫地點詳情，取得 rating、user_ratings_total、price_level、opening_hours、最近幾則 reviews（若可得）。
4) 先用規則分數（例如：加權 = rating * log1p(user_ratings_total)），再閱讀評論做語義評估（風味、一致性、環境、服務、近期負評）。
5) 最後輸出：Top 5 咖啡廳 + Top 5 餐廳的表格（店名、類型、評分、評分數、代表評論摘要、適合族群、地址與 Google Maps 連結），並附上簡短解釋排序依據。
注意：
- 請使用 maps_toolset 來執行此任務
- 優先近期評論；若評論疑似機械式/置評，降低權重。
- 價格與營業時段僅作輔助，若資訊缺失不用硬湊。
"""

# === Build Agent ===
root_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="maps_recommendation",
    instruction=SYSTEM_INSTRUCTION,
    tools=[maps_toolset],
)

# === run query function ===
async def run_query(address: str, radius_m: int = 2000) -> str:
    """
    Run the map recommendation agent query and return the result as a string.
    
    Args:
        address: The address or location to search around.
        radius_m: Search radius in meters (default: 2000).
    
    Returns:
        The agent's response as a string.
    """
    # user prompt
    user_prompt = f"""
請以 {address} 為中心，在 {radius_m} 公尺內：
- 挑出最推薦的 5 間咖啡廳與 5 間餐廳
- 先比對評分與評分數，再閱讀評論文字做語義排序
- 請輸出清單 + 每家 1~2 句評論摘要 + 為何推薦
- 提供餐廳連結請使用 https://www.google.com/maps/search/?api=1&query=%E8%97%8F%E9%AE%AE%E6%B5%B7%E9%AE%AE%E7%87%92%E7%83%A4%E6%96%99%E7%90%86 這種格式。
"""
    # initialize session and artifact service
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    # create session
    session = await session_service.create_session(
        app_name=root_agent.name,
        user_id="user_1",
        state={},
    )
    
    # create runner
    runner = Runner(
        app_name=root_agent.name,
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    
    # convert user prompt to Content format
    content = types.Content(role="user", parts=[types.Part(text=user_prompt)])
    
    # collect response text
    response_text = ""
    
    # run agent and iterate through event stream
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        # collect event with text content
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
    
    # close MCP connection
    await maps_toolset.close()
    print(response_text)
    
    return response_text

if __name__ == "__main__":
    # default address is "新北市板橋"
    logging.info(GOOGLE_MAPS_API_KEY)
    asyncio.run(run_query(address="新北市板橋", radius_m=2000))
