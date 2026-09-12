import streamlit as st
import requests
import json
from typing import List
import streamlit.components.v1 as components

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="Telegram 发送工具（云端版）",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Telegram 发送工具（Streamlit Cloud 版）")
st.caption("⚠️ 服务端不保存任何信息。配置仅保存在您自己的浏览器本地。")

# ==================== 浏览器本地存储（localStorage） ====================
def get_local_storage():
    """从浏览器 localStorage 读取配置"""
    html = """
    <script>
    const data = localStorage.getItem('telegram_config');
    if (data) {
        window.parent.postMessage({type: 'local_storage', data: data}, '*');
    } else {
        window.parent.postMessage({type: 'local_storage', data: null}, '*');
    }
    </script>
    """
    result = components.html(html, height=0)
    return result

def save_to_local_storage(api_base: str, bot_token: str, chat_id: str):
    """保存配置到浏览器 localStorage"""
    config = {
        "api_base": api_base,
        "bot_token": bot_token,
        "chat_id": chat_id
    }
    config_json = json.dumps(config, ensure_ascii=False)
    # 转义特殊字符
    config_json = config_json.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    
    html = f"""
    <script>
    localStorage.setItem('telegram_config', `{config_json}`);
    window.parent.postMessage({{type: 'saved', status: 'ok'}}, '*');
    </script>
    """
    components.html(html, height=0)

def clear_local_storage():
    """清除浏览器 localStorage"""
    html = """
    <script>
    localStorage.removeItem('telegram_config');
    window.parent.postMessage({type: 'cleared', status: 'ok'}, '*');
    </script>
    """
    components.html(html, height=0)

# ==================== 读取本地配置 ====================
# 使用 session_state 缓存，避免重复读取
if "local_config" not in st.session_state:
    st.session_state.local_config = {
        "api_base": "https://api.urlnet.top/telegram",
        "bot_token": "",
        "chat_id": ""
    }

# 尝试从 Secrets 获取默认值（可选）
try:
    default_api = st.secrets.get("API_BASE", "https://api.urlnet.top/telegram")
    default_token = st.secrets.get("BOT_TOKEN", "")
    default_chat = st.secrets.get("CHAT_ID", "")
except Exception:
    default_api = "https://api.urlnet.top/telegram"
    default_token = ""
    default_chat = ""

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
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        cut_pos = text.rfind('\n', 0, max_length)
        if cut_pos == -1 or cut_pos < max_length // 2:
            cut_pos = text.rfind(' ', 0, max_length)
        if cut_pos == -1 or cut_pos < max_length // 2:
            cut_pos = max_length

        chunks.append(text[:cut_pos].rstrip())
        text = text[cut_pos:].lstrip()
    return chunks

def send_text(token: str, chat_id: str, text: str, api_base: str, parse_mode: str = None) -> dict:
    chunks = split_text(text, max_length=4096)
    results = []

    for i, chunk in enumerate(chunks, 1):
        url = get_api_url(token, "sendMessage", api_base)
        payload = {"chat_id": chat_id, "text": chunk}
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

    if len(caption) > 1024:
        caption = caption[:1021] + "..."

    files = {"document": (filename, file_bytes)}
    data = {"chat_id": chat_id, "caption": caption}

    try:
        resp = requests.post(url, data=data, files=files, timeout=120)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.header("⚙️ 配置")

    # 使用 session_state 的值作为初始值
    api_base = st.text_input(
        "API 基础地址",
        value=st.session_state.local_config.get("api_base", default_api),
        key="api_base_input"
    )

    bot_token = st.text_input(
        "Bot Token",
        value=st.session_state.local_config.get("bot_token", default_token),
        type="password",
        key="bot_token_input"
    )

    chat_id = st.text_input(
        "群组 / 用户 ID",
        value=st.session_state.local_config.get("chat_id", default_chat),
        key="chat_id_input"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存到本地", use_container_width=True, type="primary"):
            # 更新 session_state
            st.session_state.local_config = {
                "api_base": api_base,
                "bot_token": bot_token,
                "chat_id": chat_id
            }
            # 写入浏览器 localStorage
            save_to_local_storage(api_base, bot_token, chat_id)
            st.success("✅ 已保存到您的浏览器本地！")
            st.balloons()

    with col2:
        if st.button("🗑️ 清除本地", use_container_width=True):
            st.session_state.local_config = {
                "api_base": default_api,
                "bot_token": "",
                "chat_id": ""
            }
            clear_local_storage()
            st.success("已清除本地配置")
            st.rerun()

    st.markdown("---")

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
    st.info("配置仅保存在**您自己的浏览器** localStorage 中，服务器不会存储任何敏感信息。")

# ==================== 主界面 ====================
tab1, tab2 = st.tabs(["📝 发送文字", "📁 发送文件"])

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
st.caption("配置保存在浏览器 localStorage，服务器不保存任何敏感信息。超长文字自动拆分，默认纯文本模式。")
