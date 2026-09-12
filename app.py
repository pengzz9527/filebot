import streamlit as st
import requests
import tempfile
import os
from datetime import datetime

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="Telegram 发送工具（云端版）",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Telegram 发送工具（Streamlit Cloud 版）")
st.caption("⚠️ 本版本服务端不保存任何信息（无数据库、无文件、无历史记录），刷新页面后配置需重新填写。")

# ==================== 默认值（可从 secrets 读取，也可留空） ====================
DEFAULT_API_BASE = "https://api.urlnet.top/telegram"

# 如果在 Streamlit Cloud 的 Secrets 里配置了，就自动填充（可选）
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

def send_text(token: str, chat_id: str, text: str, api_base: str) -> dict:
    url = get_api_url(token, "sendMessage", api_base)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

def send_document(token: str, chat_id: str, file_bytes: bytes, filename: str, caption: str, api_base: str) -> dict:
    url = get_api_url(token, "sendDocument", api_base)
    files = {
        "document": (filename, file_bytes)
    }
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
    st.info("本工具部署在 Streamlit Cloud，**服务端不会保存** Token、群组ID、消息或文件。")

# ==================== 主界面 ====================
tab1, tab2 = st.tabs(["📝 发送文字", "📁 发送文件"])

# ---------- 发送文字 ----------
with tab1:
    st.subheader("发送文字消息")
    text_content = st.text_area("消息内容", height=180, placeholder="在这里输入要发送的内容...")
    
    if st.button("🚀 发送文字", type="primary", use_container_width=True):
        if not bot_token or not chat_id:
            st.error("请先在左侧填写 Bot Token 和 Chat ID")
        elif not text_content.strip():
            st.warning("请输入消息内容")
        else:
            with st.spinner("发送中..."):
                result = send_text(bot_token, chat_id, text_content, api_base)
                
                if result.get("ok"):
                    msg_id = result["result"]["message_id"]
                    st.success(f"✅ 发送成功！Telegram Message ID: `{msg_id}`")
                else:
                    st.error(f"❌ 发送失败：{result.get('description', result)}")

# ---------- 发送文件 ----------
with tab2:
    st.subheader("上传并发送文件")
    uploaded_file = st.file_uploader("选择文件（支持任意类型）", type=None)
    caption = st.text_input("文件说明（可选）")
    
    if uploaded_file is not None:
        st.write(f"已选择文件：`{uploaded_file.name}` （{uploaded_file.size / 1024:.1f} KB）")
    
    if uploaded_file and st.button("🚀 上传并发送", type="primary", use_container_width=True):
        if not bot_token or not chat_id:
            st.error("请先在左侧填写 Bot Token 和 Chat ID")
        else:
            with st.spinner("正在发送文件，请稍候..."):
                # 直接使用内存中的字节，不写入磁盘
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
                    msg_id = result["result"]["message_id"]
                    st.success(f"✅ 文件发送成功！Telegram Message ID: `{msg_id}`")
                else:
                    st.error(f"❌ 发送失败：{result.get('description', result)}")

st.markdown("---")
st.caption("本应用运行在 Streamlit Cloud，所有操作均在内存中完成，服务端不保存任何用户数据。")
