import streamlit as st
import pandas as pd
import time
import json
import base64
import urllib.parse
from datetime import timedelta, date

from config import get_supabase, init_gemini
# from auth import login_signup  # NOTE: ログイン無効化中
from services import (
    get_available_gemini_models, analyze_meal_with_gemini, analyze_meal_with_advice,
    get_user_profile, update_user_profile,
    save_meal_log, get_meal_logs, delete_meal_log,
    generate_meal_advice, generate_pfc_summary,
)
from charts import create_summary_chart

# --- 初期設定 ---
st.set_page_config(page_title="AI PFC Manager", layout="centered")

# --- 背景画像の読み込み ---
import pathlib as _pathlib

def _load_bg_image():
    """背景画像をbase64エンコードして返す"""
    bg_path = _pathlib.Path(__file__).parent / "bg.png"
    if bg_path.exists():
        data = bg_path.read_bytes()
        return base64.b64encode(data).decode()
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

# --- スマホ向けCSS ---
st.markdown(f"""
<style>
    {_bg_css}

    /* コンテンツ領域に半透明グレー背景 + 黒文字 */
    .block-container {{
        background: rgba(240, 240, 240, 0.85);
        border-radius: 1rem;
        padding-top: 2.5rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        color: #111 !important;
    }}

    /* 全テキスト要素を黒系に統一 */
    .block-container h1,
    .block-container h2,
    .block-container h3,
    .block-container p,
    .block-container span,
    .block-container label,
    .block-container div,
    .block-container li {{
        color: #111 !important;
    }}
    .block-container .stMarkdown p {{
        color: #111 !important;
    }}
    /* caption は少し薄めのグレー */
    .block-container small,
    .block-container .stCaption {{
        color: #555 !important;
    }}

    /* タイトルのフォントサイズを縮小 */
    h1 {{ font-size: 1.5rem !important; }}
    h2 {{ font-size: 1.2rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}
    /* ボタンを押しやすく */
    .stButton > button {{
        width: 100%;
        min-height: 2.5rem;
    }}
    /* expanderの中身の余白を詰める */
    .streamlit-expanderContent {{
        padding: 0.3rem 0.5rem;
    }}
    /* サイドバーの幅を狭く */
    [data-testid="stSidebar"] {{
        min-width: 260px;
        max-width: 260px;
    }}
    /* タイミング選択のラジオボタンをボタン風に */
    div[data-testid="stRadio"] > div {{
        gap: 0.3rem !important;
        flex-wrap: nowrap !important;
    }}
    div[data-testid="stRadio"] > div > label {{
        background: rgba(220, 220, 220, 0.7);
        border-radius: 1.5rem;
        padding: 0.25rem 0.65rem;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.15s;
        font-size: 0.85rem;
        white-space: nowrap;
        color: #111 !important;
    }}
    div[data-testid="stRadio"] > div > label:has(input:checked) {{
        border-color: #4CAF50;
        background: rgba(76, 175, 80, 0.2);
        font-weight: bold;
    }}
    div[data-testid="stRadio"] > div > label > div:first-child {{
        display: none;  /* ラジオボタンの丸を非表示 */
    }}
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
        for pref in ["gemini-flash-latest", "gemini-3-flash", "gemini-2.5-flash"]:
            if pref in model_options:
                default_index = model_options.index(pref)
                break
        selected_model = st.selectbox("使用モデル", model_options, index=default_index)
        

        # プロフィール設定
        profile = get_user_profile(supabase, user.id)

        with st.expander("⚙️ 設定・目標", expanded=False):
            with st.form("profile_form"):
                # NOTE: 宣言機能は一時的に無効化しています。
                # decl = st.text_input("🔥 宣言", value=profile.get("declaration") or "")
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
                        # "declaration": decl,
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
    st.title("AI PFC Manager")

    # NOTE: 宣言機能は一時的に無効化しています。
    # if profile.get("declaration"):
    #     st.info(f"🔥 **Goal: {profile.get('declaration')}**")

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
            # --- 現在の集計値・目標値・プロフィールを事前に準備 ---
            _logs = get_meal_logs(supabase, user.id, current_date_str)
            _logged_meals = _logs.data if _logs and _logs.data else []
            _total_p = _total_f = _total_c = _total_cal = 0
            if _logged_meals:
                _df = pd.DataFrame(_logged_meals)
                _total_p = _df["p_val"].sum()
                _total_f = _df["f_val"].sum()
                _total_c = _df["c_val"].sum()
                _total_cal = _df["calories"].sum()

            _target_cal = profile.get("target_calories", 2000)
            _target_p = profile.get("target_p", 100)
            _target_f = profile.get("target_f", 60)
            _target_c = profile.get("target_c", 250)
            _totals = {"cal": _total_cal, "p": _total_p, "f": _total_f, "c": _total_c}
            _targets = {"cal": _target_cal, "p": _target_p, "f": _target_f, "c": _target_c}
            _profile_d = {
                "likes": profile.get("likes") or "",
                "dislikes": profile.get("dislikes") or "",
                "preferences": profile.get("preferences") or "",
            }

            # --- PFC解析 + アドバイスを1回のAPI呼び出しで取得 ---
            result = analyze_meal_with_advice(
                food_text, selected_model, _profile_d,
                _logged_meals, _totals, _targets, meal_type
            )
            if result:
                p, f, c, cal, advice = result
                save_meal_log(supabase, user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)

                # アドバイスをキャッシュに直接保存（2回目のAPI呼び出し不要）
                if advice:
                    if "advice_cache" not in st.session_state:
                        st.session_state["advice_cache"] = {}
                    st.session_state["advice_cache"][current_date_str] = advice
                    # refreshフラグは立てない（既にアドバイス取得済み）
                    st.session_state["advice_needs_refresh"] = False

                st.success(f"記録しました！ {cal}kcal")
                time.sleep(1)
                st.rerun()

    # --- グラフ + アドバイス ---

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
    chart_fig = create_summary_chart(chart_data)
    st.pyplot(chart_fig)

    # --- PFCサマリー（常に表示） ---
    totals = {"cal": total_cal, "p": total_p, "f": total_f, "c": total_c}
    targets = {"cal": target_cal, "p": target_p, "f": target_f, "c": target_c}
    logged_meals = logs.data if logs and logs.data else []

    # PFCサマリー行を表示（AIを使わない、常に表示）
    summary_line = generate_pfc_summary(totals, targets)
    st.markdown(f"<p style='font-size:1.2rem; font-weight:bold; margin:0.5rem 0;'>{summary_line}</p>", unsafe_allow_html=True)

    # --- AIアドバイス ---
    # session_stateでアドバイスをキャッシュ（日付ごと）
    if "advice_cache" not in st.session_state:
        st.session_state["advice_cache"] = {}

    # エラー抑制のための設定
    ADVICE_ERROR_COOLDOWN = 60  # エラー後の再試行待機時間（秒）
    advice_error_key = "advice_error_until"
    current_time = time.time()
    error_until = st.session_state.get(advice_error_key, 0)

    # キャッシュキー（日付）
    cache_key = current_date_str

    # 再取得が必要かどうかを判定
    needs_refresh = st.session_state.get("advice_needs_refresh", False)
    has_cache = cache_key in st.session_state["advice_cache"]

    advice_text = None
    error_msg = None
    is_loading = False

    # クールダウン中かチェック
    if current_time < error_until:
        remaining = int(error_until - current_time)
        st.warning(f"⚠️ AIが混み合っています。{remaining}秒後に再試行してください。")
    else:
        # APIを呼ぶ条件：再取得フラグが立っている場合のみ
        if needs_refresh:
            is_loading = True
            with st.spinner("🏋️ アドバイスを考え中..."):
                try:
                    profile_d = {
                        "likes": profile.get("likes") or "",
                        "dislikes": profile.get("dislikes") or "",
                        "preferences": profile.get("preferences") or "",
                    }
                    advice_text = generate_meal_advice(
                        selected_model, profile_d, logged_meals, totals, targets
                    )
                    # 成功したらキャッシュに保存
                    st.session_state["advice_cache"][cache_key] = advice_text
                    # フラグをリセット
                    st.session_state["advice_needs_refresh"] = False
                    # エラー状態をクリア
                    if advice_error_key in st.session_state:
                        del st.session_state[advice_error_key]
                except Exception as e:
                    error_msg = str(e)
                    # エラー発生時はクールダウンを設定
                    st.session_state[advice_error_key] = current_time + ADVICE_ERROR_COOLDOWN
                    # フラグはリセット（連続リトライ防止）
                    st.session_state["advice_needs_refresh"] = False

                    if "429" in error_msg:
                        # RPDは太平洋時間の午前0時にリセット（日本時間17時頃）
                        st.warning("⚠️ AIの利用制限に達しました。日本時間の17時以降に再試行してください。")
                    else:
                        st.warning("⚠️ AIアドバイスを取得できませんでした")
        elif has_cache:
            # キャッシュから取得
            advice_text = st.session_state["advice_cache"].get(cache_key)

    # AIアドバイス表示
    is_cooldown = current_time < error_until
    if advice_text:
        st.subheader("💡 AIアドバイス")
        formatted = advice_text.replace("\n", "  \n")
        st.markdown(formatted)

        # 再読み込みボタン（クールダウン中は無効化）
        if st.button("🔄 アドバイスを再取得", disabled=is_cooldown):
            st.session_state["advice_needs_refresh"] = True
            st.rerun()
    elif error_msg is None and not is_cooldown:
        # AIアドバイスがまだない場合は取得ボタンを表示
        if st.button("🤖 AIアドバイスを取得"):
            st.session_state["advice_needs_refresh"] = True
            st.rerun()

    # --- 履歴 ---
    MEAL_ORDER = {"朝食": 0, "昼食": 1, "夕食": 2, "間食": 3}
    st.subheader("履歴")
    if logs and logs.data:
        sorted_logs = sorted(logs.data, key=lambda x: MEAL_ORDER.get(x["meal_type"], 9))
        for log in sorted_logs:
            with st.expander(f"{log['meal_type']}: {log['food_name'][:15]}..."):
                st.write(f"**{log['food_name']}**")
                st.write(f"🔥 {log['calories']}kcal | P:{log['p_val']} F:{log['f_val']} C:{log['c_val']}")
                if st.button("削除", key=f"del_{log['id']}"):
                    delete_meal_log(supabase, log['id'])
                    st.rerun()
    else:
        st.info("まだ記録がありません")

    # --- 共有 ---
    st.divider()
    st.subheader("共有")

    # 共有テキスト生成
    share_lines = [f"🍽️ {display_date} の食事記録"]
    if logged_meals:
        sorted_share = sorted(logged_meals, key=lambda x: MEAL_ORDER.get(x["meal_type"], 9))
        for m in sorted_share:
            share_lines.append(
                f"・{m['meal_type']}: {m['food_name']} "
                f"({m['calories']}kcal / P:{m['p_val']} F:{m['f_val']} C:{m['c_val']})"
            )
        share_lines.append(f"\n合計: {int(total_cal)}kcal（P:{int(total_p)}g F:{int(total_f)}g C:{int(total_c)}g）")
        share_lines.append(f"目標: {target_cal}kcal（P:{target_p}g F:{target_f}g C:{target_c}g）")
    else:
        share_lines.append("記録なし")
    share_text = "\n".join(share_lines)

    # LINEで共有
    line_text = urllib.parse.quote(share_text)
    st.markdown(
        f"""
        <a href="https://line.me/R/share?text={line_text}" target="_blank" style="
            display:block; width:100%; padding:0.5rem; margin-bottom:0.5rem;
            border:1px solid #06C755; border-radius:0.5rem;
            background:#06C755; color:white; text-align:center;
            text-decoration:none; font-size:0.9rem; box-sizing:border-box;
        ">💬 LINEで共有</a>
        """,
        unsafe_allow_html=True,
    )

    # クリップボードにコピー（JavaScript）
    share_text_escaped = base64.b64encode(share_text.encode()).decode()
    st.markdown(
        f"""
        <button onclick="
            const text = atob('{share_text_escaped}');
            navigator.clipboard.writeText(text).then(() => {{
                this.textContent = '✅ コピーしました！';
                setTimeout(() => {{ this.textContent = '📋 クリップボードにコピー'; }}, 2000);
            }});
        " style="
            width:100%; padding:0.5rem; margin-bottom:0.5rem;
            border:1px solid #ccc; border-radius:0.5rem;
            background:var(--secondary-background-color);
            color:inherit; cursor:pointer; font-size:0.9rem;
        ">📋 クリップボードにコピー</button>
        """,
        unsafe_allow_html=True,
    )


# --- アプリ起動 ---
# NOTE: ログイン機能は一時的に無効化しています。
#       Streamlitの制限上アプリがpublicのため、認証処理をスキップしています。
#       再度有効にする場合は、以下のコメントアウトを解除してください。
# if "user" not in st.session_state:
#     login_signup(supabase)
# else:
#     main_app()
main_app()
