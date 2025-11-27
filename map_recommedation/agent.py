import asyncio
import logging
import os
from typing import Optional

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
1) 先將使用者給的地點地理編碼成經緯度。
2) 搜尋 2 公里內的「咖啡廳」與「餐廳」各 8 家做為候選。
3) 對每個候選呼叫地點詳情，取得 rating、user_ratings_total、price_level、opening_hours、最近幾則 reviews（若可得）。
4) 先用規則分數（例如：加權 = rating * log1p(user_ratings_total)），再閱讀評論做語義評估（風味、一致性、環境、服務、近期負評）。
5) 最後輸出：Top 3-5 咖啡廳 + Top 3-5 餐廳的條列式清單（店名、類型、評分、評分數、代表評論摘要、適合族群、地址與 Google Maps 連結），並附上簡短解釋排序依據，但總共不得多於1000字。
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
async def run_query(
    address: Optional[str],
    user_id: str,
    radius_m: int = 2000,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> str:
    """
    Run the map recommendation agent query and return the result as a string.

    Args:
        address (Optional[str]): Human readable address (if available).
        user_id (str): LINE user id used for session management.
        radius_m (int): Search radius in meters.
        latitude (Optional[float]): Latitude from LINE location event.
        longitude (Optional[float]): Longitude from LINE location event.

    Returns:
        str: Agent response text.

    Raises:
        ValueError: If both address and coordinates are missing.
    """
    if not address and (latitude is None or longitude is None):
        raise ValueError("address 或經緯度需至少提供一種資訊。")

    logging.info(
        "[run_query] 開始執行美食推薦查詢 - user_id: %s, address: %s, "
        "latitude: %s, longitude: %s, radius_m: %s",
        user_id,
        address,
        latitude,
        longitude,
        radius_m,
    )

    # user prompt
    location_lines = []
    if address:
        location_lines.append(f"地址：{address}")
    if latitude is not None and longitude is not None:
        location_lines.append(f"經緯度：{latitude:.6f}, {longitude:.6f}")
    location_desc = "\n".join(location_lines)
    user_prompt = f"""
請以以下位置為中心：
{location_desc}
並在 {radius_m} 公尺內：
- 挑出最推薦的 3-5 間咖啡廳與 3-5 間餐廳
- 先比對評分與評分數，再閱讀評論文字做語義排序
- 請輸出條列式清單 + 每家 1~2 句評論摘要 + 為何推薦
- 提供餐廳連結請使用 https://www.google.com/maps/search/?api=1&query=%E8%97%8F%E9%AE%AE%E6%B5%B7%E9%AE%AE%E7%87%92%E7%83%A4%E6%96%99%E7%90%86 這種格式。
"""
    logging.info(
        "[run_query] 已建立使用者提示 - address: %s, latitude: %s, longitude: %s, radius_m: %s",
        address,
        latitude,
        longitude,
        radius_m,
    )
    
    # initialize session and artifact service
    logging.info(f"[run_query] 初始化 session 和 artifact service")
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    # create session
    logging.info(f"[run_query] 建立 session - user_id: {user_id}, app_name: {root_agent.name}")
    session = await session_service.create_session(
        app_name=root_agent.name,
        user_id=user_id,
        state={},
    )
    logging.info(f"[run_query] Session 建立成功 - session_id: {session.id}, user_id: {session.user_id}")
    
    # create runner
    logging.info(f"[run_query] 建立 Runner")
    runner = Runner(
        app_name=root_agent.name,
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    
    # convert user prompt to Content format
    content = types.Content(role="user", parts=[types.Part(text=user_prompt)])
    logging.info(f"[run_query] 開始執行 agent - session_id: {session.id}")
    
    # collect response text
    response_text = ""
    event_count = 0
    
    # run agent and iterate through event stream
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        event_count += 1
        # collect event with text content
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
                    logging.debug(f"[run_query] 收到事件 #{event_count}，累積回應長度: {len(response_text)} 字元")
    
    logging.info(f"[run_query] Agent 執行完成 - 總共收到 {event_count} 個事件，回應長度: {len(response_text)} 字元")
    
    # close MCP connection
    logging.info(f"[run_query] 關閉 MCP 連線")
    await maps_toolset.close()
    logging.info(f"[run_query] MCP 連線已關閉")
    
    logging.info(f"[run_query] 查詢完成 - user_id: {user_id}, address: {address}, 回應長度: {len(response_text)} 字元")
    
    return response_text

if __name__ == "__main__":
    # default address is "新北市板橋"
    logging.info(f"[main] run agent.py directly")
    asyncio.run(run_query(address="新北市板橋", user_id="test_user", radius_m=2000))
