import pytest
import pytest_asyncio
from pathlib import Path

from llm_gateway import LLMGatewayClient, ChatRequest, ChatSession
from llm_gateway.settings import load_gateway_config
from llm_gateway.config import SessionConfig


TEST_DIR = Path(__file__).resolve().parent
DEMO_IMG = TEST_DIR / "demo.png"


# ==============================
# 全局配置
# ==============================
gateway_config = load_gateway_config()


# ==============================
# 异步client fixture
# session级别：整个测试文件只创建一次连接池
# ==============================
@pytest_asyncio.fixture(scope="session")
async def client():
    async with LLMGatewayClient(gateway_config) as c:
        yield c


# ==============================
# TEST1 无历史单轮文本
# ==============================
@pytest.mark.asyncio
async def test_case1_single_text_no_history(client):
    print("\n================ CASE1 单轮文本无历史 ================")

    resp = await client.chat(ChatRequest(prompt="请用一句话介绍人工智能。"))
    print(resp)

    assert resp is not None
    assert len(resp) > 0


# ==============================
# TEST2 request级system prompt
# ==============================
@pytest.mark.asyncio
async def test_case2_single_text_request_system(client):
    print("\n================ CASE2 request级system prompt ================")

    resp = await client.chat(
        ChatRequest(
            prompt="请介绍一下苹果公司。",
            system_prompt="你现在是一名金融分析师，请从上市公司角度回答。",
        )
    )
    print(resp)

    assert resp is not None
    assert len(resp) > 0


# ==============================
# TEST3 session多轮文本对话
# ==============================
@pytest.mark.asyncio
async def test_case3_session_multi_turn(client):
    print("\n================ CASE3 session多轮文本 ================")

    session = ChatSession()

    resp1 = await client.chat(ChatRequest(prompt="我叫张三。"), session=session)
    print("A1:", resp1)

    resp2 = await client.chat(ChatRequest(prompt="你记得我叫什么吗？"), session=session)
    print("A2:", resp2)

    assert resp2 is not None
    assert len(resp2) > 0


# ==============================
# TEST4 session级system prompt
# ==============================
@pytest.mark.asyncio
async def test_case4_session_system_prompt(client):
    print("\n================ CASE4 session级system prompt ================")

    session = ChatSession(
        SessionConfig(system_prompt="你是一名专业法律顾问，请使用法律咨询口吻作答。")
    )

    resp1 = await client.chat(
        ChatRequest(prompt="劳动合同未签订有什么风险？"),
        session=session,
    )
    print("A1:", resp1)

    resp2 = await client.chat(
        ChatRequest(prompt="如果员工已经离职呢？"),
        session=session,
    )
    print("A2:", resp2)

    assert resp2 is not None


# ==============================
# TEST5 global默认system prompt
# ==============================
@pytest.mark.asyncio
async def test_case5_global_system_prompt(client):
    print("\n================ CASE5 global默认system prompt ================")

    resp = await client.chat(ChatRequest(prompt="你是谁？"))
    print(resp)

    assert resp is not None


# ==============================
# TEST6 system prompt三级优先级
# ==============================
@pytest.mark.asyncio
async def test_case6_system_priority(client):
    print("\n================ CASE6 system prompt优先级 ================")

    session = ChatSession(SessionConfig(system_prompt="你是一名医生。"))

    resp = await client.chat(
        ChatRequest(
            prompt="请介绍一下感冒。",
            system_prompt="你是一名儿童科普作家，请用儿童能听懂的话解释。",
        ),
        session=session,
    )
    print(resp)

    assert resp is not None


# ==============================
# TEST7 单轮图片识别
# ==============================
@pytest.mark.asyncio
async def test_case7_single_image_ocr(client):
    print("\n================ CASE7 单轮图片识别 ================")

    img = DEMO_IMG.read_bytes()

    resp = await client.chat(
        ChatRequest(
            prompt="请识别图片中的主要文字内容。",
            image_bytes=img,
        )
    )
    print(resp)

    assert resp is not None


# ==============================
# TEST8 图片多轮追问
# ==============================
@pytest.mark.asyncio
async def test_case8_image_multi_turn(client):
    print("\n================ CASE8 图片多轮追问 ================")

    img = DEMO_IMG.read_bytes()

    session = ChatSession(SessionConfig(system_prompt="你是一名发票OCR识别助手。"))

    resp1 = await client.chat(
        ChatRequest(prompt="请识别这张发票。", image_bytes=img),
        session=session,
    )
    print("A1:", resp1)

    resp2 = await client.chat(
        ChatRequest(prompt="其中总金额是多少？"),
        session=session,
    )
    print("A2:", resp2)

    resp3 = await client.chat(
        ChatRequest(prompt="开票日期是什么时候？"),
        session=session,
    )
    print("A3:", resp3)

    assert resp3 is not None


# ==============================
# TEST9 流式输出
# ==============================
@pytest.mark.asyncio
async def test_case9_stream_no_history(client):
    print("\n================ CASE9 流式输出 ================")

    full = ""
    async for chunk in client.stream_chat(
        ChatRequest(prompt="请详细介绍一下机器学习的发展历史。")
    ):
        print(chunk, end="", flush=True)
        full += chunk

    print()

    assert len(full) > 0


# ==============================
# TEST10 流式 + session多轮
# ==============================
@pytest.mark.asyncio
async def test_case10_stream_with_session(client):
    print("\n================ CASE10 流式 + session历史 ================")

    session = ChatSession()

    full = ""
    async for chunk in client.stream_chat(
        ChatRequest(prompt="我准备写一篇关于人工智能的论文，请给我一个提纲。"),
        session=session,
    ):
        print(chunk, end="", flush=True)
        full += chunk

    print("\n------ 第二轮追问 ------")

    async for chunk in client.stream_chat(
        ChatRequest(prompt="请把第二部分展开详细一些。"),
        session=session,
    ):
        print(chunk, end="", flush=True)
        full += chunk


# ==============================
# TEST11 JSON模式
# ==============================
@pytest.mark.asyncio
async def test_case11_json_mode(client):
    print("\n================ CASE11 JSON模式 ================")

    resp = await client.chat(
        ChatRequest(
            prompt="请返回一个包含name和age字段的json。",
            json_mode=True,
        )
    )
    print(resp)

    assert resp is not None


# ==============================
# TEST12 thinking模式
# ==============================
@pytest.mark.asyncio
async def test_case12_enable_thinking(client):
    print("\n================ CASE12 thinking模式 ================")

    resp = await client.chat(
        ChatRequest(
            prompt="请推理 135 * 278 的结果。",
            enable_thinking=True,
        )
    )
    print(resp)

    assert resp is not None
