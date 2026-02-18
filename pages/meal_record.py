import streamlit as st
import base64
import pathlib as _pathlib
from datetime import date

from config import get_supabase, init_gemini

# --- ページ設定（必ず最初に1回だけ） ---
st.set_page_config(page_title="AI PFC Manager", layout="centered")

# --- 背景画像 ---
def _load_bg_image():
    bg_path = _pathlib.Path(__file__).parent / "bg.png"
    if bg_path.exists():
        return base64.b64encode(bg_path.read_bytes()).decode()
    return None

_bg_b64 = _load_bg_image()
_bg_css = ""
if _bg_b64:
    _bg_css = f"""
    .stApp {{
        background: linear-gradient(
            rgba(0, 0, 0, 0.3),
            rgba(0, 0, 0, 0.4)
        ), url("data:image/jpeg;base64,{_bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    """

# --- 共通CSS ---
st.markdown(f"""
<style>
    {_bg_css}
    .block-container {{
        background: rgba(240, 240, 240, 0.85);
        border-radius: 1rem;
        padding-top: 2.5rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        color: #111 !important;
    }}
    .block-container h1, .block-container h2, .block-container h3,
    .block-container p, .block-container span, .block-container label,
    .block-container div, .block-container li {{
        color: #111 !important;
    }}
    .block-container .stMarkdown p {{ color: #111 !important; }}
    .block-container small, .block-container .stCaption {{ color: #555 !important; }}
    h1 {{ font-size: 1.5rem !important; }}
    h2 {{ font-size: 1.2rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}
    .stButton > button {{
        width: 100%;
        min-height: 2.5rem;
        background-color: #fafdff !important;
        color: #111 !important;
        border: 1px solid #ddd !important;
    }}
    .stFormSubmitButton > button,
    div[data-testid="stFormSubmitButton"] > button {{
        background-color: #fafdff !important;
        color: #111 !important;
        border: 1px solid #ddd !important;
    }}
    .block-container textarea,
    .block-container input {{
        background-color: #fafdff !important;
        color: #111 !important;
        border: 1px solid #ccc !important;
    }}
    .block-container [data-baseweb="select"] {{
        background-color: #fafdff !important;
    }}
    .block-container [data-baseweb="select"] * {{
        color: #111 !important;
    }}
    .streamlit-expanderContent {{
        padding: 0.3rem 0.5rem;
    }}
    [data-testid="stSidebar"] {{
        min-width: 260px;
        max-width: 260px;
    }}
    div[data-testid="stRadio"] > div {{
        gap: 0.3rem !important;
        flex-wrap: nowrap !important;
    }}
    div[data-testid="stRadio"] > div > label {{
        background: rgba(220, 220, 220, 0.7);
        border-radius: 1.5rem;
        padding: 0.3rem 0.65rem;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.15s;
        font-size: 0.85rem;
        white-space: nowrap;
        color: #111 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    div[data-testid="stRadio"] > div > label:has(input:checked) {{
        border-color: #00ACC1;
        background: rgba(0, 172, 193, 0.2);
        font-weight: bold;
    }}
    div[data-testid="stRadio"] > div > label > div:first-child {{
        display: none;
    }}
</style>
""", unsafe_allow_html=True)

# --- 共通初期化 ---
supabase = get_supabase()
init_gemini()

if "current_date" not in st.session_state:
    st.session_state.current_date = date.today()

# NOTE: ログイン無効化中のデフォルトユーザー
DEFAULT_USER_ID = "d8875444-a88a-4a31-947d-2174eefb80f0"
DEFAULT_USER_EMAIL = "guest@example.com"

class _DefaultUser:
    def __init__(self):
        self.id = DEFAULT_USER_ID
        self.email = DEFAULT_USER_EMAIL

if "user" not in st.session_state:
    st.session_state["user"] = _DefaultUser()

# AIモデルのデフォルト値
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = "gemini-flash-latest"

# --- ページルーティング（Streamlit推奨方式 / グループ分け） ---
pg = st.navigation({
    "メイン": [
        st.Page("pages/meal_record.py", title="食事記録", icon="🍽️", default=True),
        st.Page("pages/dashboard.py",   title="PFCダッシュボード", icon="📊"),
    ],
    "その他": [
        st.Page("pages/settings.py", title="設定", icon="⚙️"),
    ],
})
pg.run()
