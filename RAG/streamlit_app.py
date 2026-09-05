"""Streamlit host for the custom frontend agent interface."""

from pathlib import Path
import json
import ssl
import urllib.error
import urllib.request

import streamlit as st
import streamlit.components.v1 as components
import certifi

from agents.interface_agent import handle_input


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
REFERENCE_DIR = ROOT_DIR / "reference_files"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=22.5431&longitude=114.0579"
    "&current=temperature_2m,weather_code,is_day&timezone=Asia%2FShanghai"
)


@st.cache_data(ttl=600, show_spinner=False)
def load_weather() -> dict[str, str | int]:
    """读取深圳当前天气；外网不可用时返回可用的静态兜底值。"""
    fallback = {
        "city": "深圳",
        "temperature": 26,
        "weather_code": 1,
        "is_day": 1,
    }
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(WEATHER_URL, context=context, timeout=4) as response:
            current = json.loads(response.read().decode("utf-8")).get("current", {})
        return {
            "city": "深圳",
            "temperature": round(float(current.get("temperature_2m", fallback["temperature"]))),
            "weather_code": int(current.get("weather_code", fallback["weather_code"])),
            "is_day": int(current.get("is_day", fallback["is_day"])),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return fallback


def load_reference_files() -> list[dict[str, str | int]]:
    """读取仓库指定目录中的参考文件，前端不提供上传入口。"""
    if not REFERENCE_DIR.exists():
        return []
    allowed_suffixes = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
        ".json", ".txt", ".md", ".ppt", ".pptx",
    }
    files = []
    for path in sorted(REFERENCE_DIR.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in allowed_suffixes:
            continue
        relative_path = path.relative_to(REFERENCE_DIR).as_posix()
        files.append({
            "name": path.name,
            "path": relative_path,
            "extension": path.suffix.lstrip(".").upper() or "FILE",
            "size": path.stat().st_size,
            "category": path.parent.relative_to(REFERENCE_DIR).as_posix()
            if path.parent != REFERENCE_DIR else "参考文件",
        })
    return files

agent_component = components.declare_component(
    "k_company_engineering_agent",
    path=str(FRONTEND_DIR),
)


def main() -> None:
    st.set_page_config(
        page_title="K公司工程变更Agent",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        html, body, #root, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        section.main, section.main > div,
        [data-testid="stAppViewContainer"] > .main > div {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
            min-height: 100vh;
            height: 100vh;
            overflow: hidden !important;
        }
        [data-testid="stVerticalBlock"],
        .stVerticalBlock,
        .stElementContainer,
        .stCustomComponentV1 {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"], footer { display: none; }
        .stApp { background: #020617; }
        .block-container { max-width: none; padding: 0 !important; }
        iframe {
            display: block !important;
            width: 100% !important;
            max-width: none !important;
            height: 100vh !important;
            min-height: 100vh !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("role", "A")
    st.session_state.setdefault("response", "")
    st.session_state.setdefault("last_event", None)

    event = agent_component(
        role=st.session_state.role,
        response=st.session_state.response,
        reference_files=load_reference_files(),
        weather=load_weather(),
        default=None,
        key="agent_frontend",
    )

    if event and event != st.session_state.last_event:
        message = str(event.get("message", "")).strip()
        role = str(event.get("role", st.session_state.role)).upper()
        if message and role in {"A", "B", "C"}:
            interaction = handle_input(message, role)
            st.session_state.role = interaction["role"]
            st.session_state.response = interaction["answer"]
            st.session_state.last_event = event
            st.rerun()


if __name__ == "__main__":
    main()
