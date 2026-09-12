import streamlit as st
import requests
from typing import List

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="Telegram 发送工具（云端版）",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Telegram 发送工具（Streamlit Cloud 版）")
st.caption("⚠️ 本版本服务端不保存任何信息（无数据库、无文件、无历史记录），刷新页面后配置需重新填写。")

# ==================== 默认值（可从 Streamlit Secrets 读取） ====================
DEFAULT_API_BASE = "https://api.urlnet.top/telegram"

try:
    DEFAULT_API_BASE = st.secrets.get("API_BASE", DEFAULT_API_BASE)
    DEFAULT_BOT_TOKEN = st.secrets.get("BOT_TOKEN", "")
    DEFAULT_CHAT_ID = st.secrets.get("CHAT_ID", "")
except Exception:
    DEFAULT_BOT_TOKEN = ""
    DEFAULT_CHAT_ID = ""

# ==================== Telegram API 函数 ====================
def get_api_url(token: str, method: str, api_base: str) -> str:
    return f"{api_base.rstrip('/')}/bot{token}/{method}"

def test_bot(token: str, api_base: str) -> dict:
    url = get_api_url(token, "getMe", api_base)
    try:
        resp = requests.get(url, timeout=15)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

def split_text(text: str, max_length: int = 4096) -> List[str]:
    """把超长文字安全拆分成多段（不超过 Telegram 限制）"""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # 尽量在换行或空格处切断
        cut_pos = text.rfind('\n', 0, max_length)
        if cut_pos == -1 or cut_pos < max_length // 2:
            cut_pos = text.rfind(' ', 0, max_length)
        if cut_pos == -1 or cut_pos < max_length // 2:
            cut_pos = max_length

        chunks.append(text[:cut_pos].rstrip())
        text = text[cut_pos:].lstrip()
    return chunks

def send_text(token: str, chat_id: str, text: str, api_base: str, parse_mode: str = None) -> dict:
    """
    发送文字（自动拆分超长消息）
    parse_mode: None = 纯文本（推荐），"HTML" 或 "Markdown"
    """
    chunks = split_text(text, max_length=4096)
    results = []

    for i, chunk in enumerate(chunks, 1):
        url = get_api_url(token, "sendMessage", api_base)
        payload = {
            "chat_id": chat_id,
            "text": chunk
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, json=payload, timeout=30)
            result = resp.json()
            results.append(result)

            if not result.get("ok"):
                return {
                    "ok": False,
                    "description": f"第 {i}/{len(chunks)} 段发送失败: {result.get('description', result)}"
                }
        except Exception as e:
            return {"ok": False, "description": f"第 {i} 段发送异常: {str(e)}"}

    return {
        "ok": True,
        "result": {
            "message_id": results[-1]["result"]["message_id"],
            "total_chunks": len(chunks),
            "all_message_ids": [r["result"]["message_id"] for r in results]
        }
    }

def send_document(token: str, chat_id: str, file_bytes: bytes, filename: str, caption: str, api_base: str) -> dict:
    url = get_api_url(token, "sendDocument", api_base)

    # 文件说明最长 1024 字符
    if len(caption) > 1024:
        caption = caption[:1021] + "..."

    files = {"document": (filename, file_bytes)}
    data = {
        "chat_id": chat_id,
        "caption": caption
    }

    try:
        resp = requests.post(url, data=data, files=files, timeout=120)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.header("⚙️ 配置（仅当前会话有效）")

    api_base = st.text_input(
        "API 基础地址",
        value=DEFAULT_API_BASE,
        help="例如：https://api.urlnet.top/telegram 或 https://api.telegram.org"
    )

    bot_token = st.text_input(
        "Bot Token",
        value=DEFAULT_BOT_TOKEN,
        type="password",
        help="格式：123456:ABC-DEF..."
    )

    chat_id = st.text_input(
        "群组 / 用户 ID",
        value=DEFAULT_CHAT_ID,
        help="群组通常以 -100 开头，例如 -1003504966336"
    )

    if st.button("🔍 测试 Bot 连接", use_container_width=True):
        if not bot_token:
            st.error("请填写 Bot Token")
        else:
            with st.spinner("测试中..."):
                result = test_bot(bot_token, api_base)
                if result.get("ok"):
                    info = result["result"]
                    st.success(f"✅ 连接成功\n名称：{info.get('first_name')}\n用户名：@{info.get('username')}")
                else:
                    st.error(f"❌ 失败：{result.get('description', result)}")

    st.markdown("---")
    st.info("本工具部署在 Streamlit Cloud，**服务端不会保存** Token、群组ID、消息或文件。\n\n超长文字会自动拆分（每条 ≤ 4096 字符）。")

# ==================== 主界面 ====================
tab1, tab2 = st.tabs(["📝 发送文字", "📁 发送文件"])

# ---------- 发送文字 ----------
with tab1:
    st.subheader("发送文字消息")
    text_content = st.text_area("消息内容", height=220, placeholder="支持超长文字，会自动拆分发送...")

    col1, col2 = st.columns([3, 1])
    with col1:
        char_count = len(text_content)
        if char_count > 0:
            if char_count <= 4096:
                st.caption(f"当前字数：{char_count} / 4096（单条发送）")
            else:
                chunks_needed = (char_count + 4095) // 4096
                st.caption(f"当前字数：{char_count} → 将自动拆分为约 {chunks_needed} 条消息")
    with col2:
        enable_html = st.checkbox(
            "启用 HTML 格式",
            value=False,
            help="仅当你确认内容是合法 HTML 时才勾选，否则容易报错"
        )

    if st.button("🚀 发送文字", type="primary", use_container_width=True):
        if not bot_token or not chat_id:
            st.error("请先在左侧填写 Bot Token 和 Chat ID")
        elif not text_content.strip():
            st.warning("请输入消息内容")
        else:
            with st.spinner("发送中（超长文字会自动拆分）..."):
                parse_mode = "HTML" if enable_html else None
                result = send_text(bot_token, chat_id, text_content, api_base, parse_mode=parse_mode)

                if result.get("ok"):
                    total = result["result"].get("total_chunks", 1)
                    if total > 1:
                        st.success(f"✅ 发送成功！共拆分为 **{total}** 条消息。")
                        st.write("消息 ID 列表：", result["result"]["all_message_ids"])
                    else:
                        st.success(f"✅ 发送成功！Message ID: `{result['result']['message_id']}`")
                else:
                    st.error(f"❌ 发送失败：{result.get('description', result)}")

# ---------- 发送文件 ----------
with tab2:
    st.subheader("上传并发送文件")
    uploaded_file = st.file_uploader("选择文件（支持任意类型）", type=None)
    caption = st.text_input("文件说明（可选，最长 1024 字符）")

    if uploaded_file is not None:
        st.write(f"已选择文件：`{uploaded_file.name}` （{uploaded_file.size / 1024:.1f} KB）")

    if uploaded_file and st.button("🚀 上传并发送", type="primary", use_container_width=True):
        if not bot_token or not chat_id:
            st.error("请先在左侧填写 Bot Token 和 Chat ID")
        else:
            with st.spinner("正在发送文件，请稍候..."):
                file_bytes = uploaded_file.getvalue()
                result = send_document(
                    token=bot_token,
                    chat_id=chat_id,
                    file_bytes=file_bytes,
                    filename=uploaded_file.name,
                    caption=caption,
                    api_base=api_base
                )

                if result.get("ok"):
                    st.success(f"✅ 文件发送成功！Message ID: `{result['result']['message_id']}`")
                else:
                    st.error(f"❌ 发送失败：{result.get('description', result)}")

st.markdown("---")
st.caption("Telegram 文字消息限制 4096 字符，本工具已自动处理超长内容拆分。默认使用纯文本模式，避免解析错误。")
