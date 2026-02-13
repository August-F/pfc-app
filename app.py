import streamlit as st
import pandas as pd
import time
from datetime import timedelta, date

from config import get_supabase, init_gemini
# from auth import login_signup  # NOTE: ログイン無効化中
from services import (
    get_available_gemini_models, analyze_meal_with_gemini,
    get_user_profile, update_user_profile,
    save_meal_log, get_meal_logs, delete_meal_log,
)
from charts import create_summary_chart

# --- 初期設定 ---
st.set_page_config(page_title="AI PFC Manager", layout="centered")

# --- スマホ向けCSS ---
st.markdown("""
<style>
    /* メインコンテンツの余白を詰める */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }
    /* タイトルのフォントサイズを縮小 */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1.1rem !important; }
    /* ボタンを押しやすく */
    .stButton > button {
        width: 100%;
        min-height: 2.5rem;
    }
    /* expanderの中身の余白を詰める */
    .streamlit-expanderContent {
        padding: 0.3rem 0.5rem;
    }
    /* サイドバーの幅を狭く */
    [data-testid="stSidebar"] {
        min-width: 260px;
        max-width: 260px;
    }
    /* タイミング選択のラジオボタンをボタン風に */
    div[data-testid="stRadio"] > div {
        gap: 0.3rem !important;
        flex-wrap: nowrap !important;
    }
    div[data-testid="stRadio"] > div > label {
        background: var(--secondary-background-color);
        border-radius: 1.5rem;
        padding: 0.25rem 0.65rem;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.15s;
        font-size: 0.85rem;
        white-space: nowrap;
    }
    div[data-testid="stRadio"] > div > label:has(input:checked) {
        border-color: #4CAF50;
        background: rgba(76, 175, 80, 0.15);
        font-weight: bold;
    }
    div[data-testid="stRadio"] > div > label > div:first-child {
        display: none;  /* ラジオボタンの丸を非表示 */
    }
</style>
""", unsafe_allow_html=True)
supabase = get_supabase()
init_gemini()

if "current_date" not in st.session_state:
    st.session_state.current_date = date.today()

# NOTE: ログイン無効化中のデフォルトユーザー
#       再度ログインを有効にする場合は、この部分を削除してください。
DEFAULT_USER_ID = "d8875444-a88a-4a31-947d-2174eefb80f0"
DEFAULT_USER_EMAIL = "guest@example.com"

class _DefaultUser:
    """ログイン無効化時に使用するダミーユーザー"""
    def __init__(self):
        self.id = DEFAULT_USER_ID
        self.email = DEFAULT_USER_EMAIL

if "user" not in st.session_state:
    st.session_state["user"] = _DefaultUser()


# --- サイドバー ---
def render_sidebar(user):
    """サイドバーを描画し、(選択モデル, プロフィール) を返す"""
    with st.sidebar:
        # NOTE: ログイン無効化中のため、ログアウトボタンを非表示にしています。
        # st.write(f"User: {user.email}")
        # if st.button("ログアウト"):
        #     supabase.auth.sign_out()
        #     st.session_state.pop("user", None)
        #     st.session_state.pop("session", None)
        #     st.rerun()

        st.divider()

        # AIモデル選択
        st.header("🤖 AIモデル設定")
        model_options = get_available_gemini_models()
        default_index = 0
        for pref in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            if pref in model_options:
                default_index = model_options.index(pref)
                break
        selected_model = st.selectbox("使用モデル", model_options, index=default_index)

        st.divider()

        # プロフィール設定
        profile = get_user_profile(supabase, user.id)

        with st.expander("⚙️ 設定・目標", expanded=False):
            with st.form("profile_form"):
                decl = st.text_input("🔥 宣言", value=profile.get("declaration") or "")
                st.subheader("目標数値")
                t_cal = st.number_input("目標カロリー (kcal)", value=profile.get("target_calories", 2000))
                t_p = st.number_input("目標 P (g)", value=profile.get("target_p", 100))
                t_f = st.number_input("目標 F (g)", value=profile.get("target_f", 60))
                t_c = st.number_input("目標 C (g)", value=profile.get("target_c", 250))
                st.subheader("好み・要望")
                likes = st.text_area("好きな食べ物", value=profile.get("likes") or "")
                dislikes = st.text_area("苦手な食べ物", value=profile.get("dislikes") or "")
                prefs = st.text_area("その他要望", value=profile.get("preferences") or "")

                if st.form_submit_button("設定を保存"):
                    updates = {
                        "declaration": decl,
                        "target_calories": t_cal,
                        "target_p": t_p, "target_f": t_f, "target_c": t_c,
                        "likes": likes, "dislikes": dislikes, "preferences": prefs,
                    }
                    update_user_profile(supabase, user.id, updates)
                    st.success("保存しました")
                    time.sleep(0.5)
                    st.rerun()

    return selected_model, profile


# --- メインアプリ ---
def main_app():
    user = st.session_state["user"]
    selected_model, profile = render_sidebar(user)

    # --- ヘッダー ---
    st.title("🍽️ AI PFC Manager")

    if profile.get("declaration"):
        st.info(f"🔥 **Goal: {profile.get('declaration')}**")

    # --- 日付ナビゲーション ---
    # query_paramsから日付を復元
    params = st.query_params
    if "date" in params:
        try:
            st.session_state.current_date = date.fromisoformat(params["date"])
        except ValueError:
            pass

    prev_date = (st.session_state.current_date - timedelta(days=1)).isoformat()
    next_date = (st.session_state.current_date + timedelta(days=1)).isoformat()
    display_date = st.session_state.current_date.strftime("%m/%d (%a)")

    st.markdown(
        f'<div style="display:flex; justify-content:center; align-items:center; '
        f'gap:1.2rem; margin:0.5rem 0;">'
        f'<a href="?date={prev_date}" target="_self" '
        f'style="text-decoration:none; font-size:1.5rem;">◀</a>'
        f'<span style="font-weight:bold; font-size:1.2rem;">{display_date}</span>'
        f'<a href="?date={next_date}" target="_self" '
        f'style="text-decoration:none; font-size:1.5rem;">▶</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # --- データ取得 ---
    current_date_str = st.session_state.current_date.isoformat()
    logs = get_meal_logs(supabase, user.id, current_date_str)

    # --- 食事入力 ---
    st.subheader("📝 食事を記録")
    with st.form("meal_input"):
        meal_type = st.radio("タイミング", ["朝食", "昼食", "夕食", "間食"], horizontal=True)
        food_text = st.text_area("食べたもの", height=80)
        submitted = st.form_submit_button("AI解析して記録")

        if submitted:
            result = analyze_meal_with_gemini(food_text, selected_model)
            if result:
                p, f, c, cal = result
                save_meal_log(supabase, user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)
                st.success(f"記録しました！ {cal}kcal")
                time.sleep(1)
                st.rerun()

    st.divider()

    # --- グラフ + アドバイス ---
    st.subheader("📊 本日の進捗")

    # 集計
    total_p = total_f = total_c = total_cal = 0
    if logs and logs.data:
        df = pd.DataFrame(logs.data)
        total_p = df["p_val"].sum()
        total_f = df["f_val"].sum()
        total_c = df["c_val"].sum()
        total_cal = df["calories"].sum()

    target_cal = profile.get("target_calories", 2000)
    target_p = profile.get("target_p", 100)
    target_f = profile.get("target_f", 60)
    target_c = profile.get("target_c", 250)

    chart_data = {
        "Cal": {"current": total_cal, "target": target_cal, "unit": "kcal"},
        "P":   {"current": total_p,   "target": target_p,   "unit": "g"},
        "F":   {"current": total_f,   "target": target_f,   "unit": "g"},
        "C":   {"current": total_c,   "target": target_c,   "unit": "g"},
    }
    st.pyplot(create_summary_chart(chart_data))

    # アドバイス
    st.divider()
    st.info("💡 AIアドバイス")
    rem_cal = target_cal - total_cal
    if rem_cal > 0:
        st.write(f"あと **{rem_cal} kcal** 食べられます。")
    else:
        st.write(f"目標カロリーを **{abs(rem_cal)} kcal** オーバーしています！")

    st.divider()

    # --- 履歴 ---
    st.subheader("履歴")
    if logs and logs.data:
        for log in logs.data:
            with st.expander(f"{log['meal_type']}: {log['food_name'][:15]}..."):
                st.write(f"**{log['food_name']}**")
                st.write(f"🔥 {log['calories']}kcal | P:{log['p_val']} F:{log['f_val']} C:{log['c_val']}")
                if st.button("削除", key=f"del_{log['id']}"):
                    delete_meal_log(supabase, log['id'])
                    st.rerun()
    else:
        st.info("まだ記録がありません")


# --- アプリ起動 ---
# NOTE: ログイン機能は一時的に無効化しています。
#       Streamlitの制限上アプリがpublicのため、認証処理をスキップしています。
#       再度有効にする場合は、以下のコメントアウトを解除してください。
# if "user" not in st.session_state:
#     login_signup(supabase)
# else:
#     main_app()
main_app()
