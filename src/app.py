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
    }}
    .block-container textarea,
    .block-container input {{
        background-color: #fafdff !important;
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

# --- スワイプナビゲーション + ページインジケーター ---
st.html("""
<script>
(function() {
    // ページ順序の定義
    var pages = ["/meal_record", "/dashboard", "/nutrition"];

    // 現在ページのインデックスを取得
    function getCurrentIndex() {
        var path = window.location.pathname;
        // デフォルトページ "/" は meal_record と同等
        if (path === "/" || path === "") return 0;
        var clean = path.replace(/\/$/, "");
        for (var i = 0; i < pages.length; i++) {
            if (clean === pages[i]) return i;
        }
        return -1; // 設定ページ等
    }

    // --- ページインジケータードット ---
    function updateDots() {
        var idx = getCurrentIndex();
        var existing = document.getElementById("pfc-page-dots");
        if (existing) existing.remove();
        if (idx < 0) return;

        var container = document.createElement("div");
        container.id = "pfc-page-dots";
        container.style.cssText = "position:fixed;bottom:14px;left:50%;transform:translateX(-50%);"
            + "z-index:999999;display:flex;gap:8px;pointer-events:none;";
        for (var i = 0; i < pages.length; i++) {
            var dot = document.createElement("div");
            dot.style.cssText = "width:8px;height:8px;border-radius:50%;transition:all 0.2s;"
                + (i === idx
                    ? "background:#00ACC1;transform:scale(1.3);"
                    : "background:rgba(150,150,150,0.5);");
            container.appendChild(dot);
        }
        document.body.appendChild(container);
    }
    updateDots();

    // --- スワイプ検出 ---
    if (window.__pfc_swipe_initialized) return;
    window.__pfc_swipe_initialized = true;

    var startX = 0, startY = 0, startTime = 0;
    var THRESHOLD = 50;   // 最小スワイプ距離(px)
    var MAX_TIME = 500;   // 最大スワイプ時間(ms)

    // スワイプを無視すべき要素かチェック
    function shouldIgnore(el) {
        var tag = el.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT"
            || tag === "BUTTON" || tag === "A" || tag === "CANVAS") return true;
        if (el.closest && (el.closest('[data-testid="stSlider"]')
            || el.closest('[data-testid="stDataFrame"]'))) return true;
        return false;
    }

    document.addEventListener("touchstart", function(e) {
        if (e.touches.length !== 1) return;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        startTime = Date.now();
    }, { passive: true });

    document.addEventListener("touchend", function(e) {
        if (e.changedTouches.length !== 1) return;
        if (shouldIgnore(e.target)) return;

        var dx = e.changedTouches[0].clientX - startX;
        var dy = e.changedTouches[0].clientY - startY;
        var elapsed = Date.now() - startTime;

        if (Math.abs(dy) > Math.abs(dx)) return;
        if (Math.abs(dx) < THRESHOLD) return;
        if (elapsed > MAX_TIME) return;

        var idx = getCurrentIndex();
        if (idx < 0) return;

        var nextIdx = dx < 0 ? idx + 1 : idx - 1;
        if (nextIdx < 0 || nextIdx >= pages.length) return;

        window.location.pathname = pages[nextIdx];
    }, { passive: true });
})();
</script>
""")

# --- ページルーティング（Streamlit推奨方式 / グループ分け） ---
pg = st.navigation({
    "メイン": [
        st.Page("pages/meal_record.py", title="食事記録", icon="🍽️", default=True),
        st.Page("pages/dashboard.py",   title="PFCダッシュボード", icon="📊"),
        st.Page("pages/nutrition.py",   title="栄養成分", icon="🥗"),
    ],
    "その他": [
        st.Page("pages/settings.py", title="設定", icon="⚙️"),
    ],
})
pg.run()
