"""
🍽️ 食事記録ページ
"""

import streamlit as st
import pandas as pd
import time
import base64
import urllib.parse
from datetime import timedelta, date

from config import get_supabase
from services import (
    analyze_meal_with_advice,
    get_user_profile,
    save_meal_log, get_meal_logs, delete_meal_log,
    generate_meal_advice, generate_pfc_summary,
)
from charts import create_summary_chart

supabase = get_supabase()

# --- ページ固有の余白縮小CSS ---
st.markdown("""
<style>
    /* サブヘッダーの余白縮小 */
    .block-container h2 { margin-top: 0.4rem !important; margin-bottom: 0.2rem !important; }
    .block-container h3 { margin-top: 0.3rem !important; margin-bottom: 0.1rem !important; }
    /* divider の余白縮小 */
    .block-container hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
    /* expander の余白縮小 */
    .streamlit-expanderHeader { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; }
    /* primary ボタンと form submit ボタンの見た目を統一 */
    button[data-testid="baseButton-primary"],
    button[data-testid="baseButton-primaryFormSubmit"] {
        background-color: #00ACC1 !important;
        color: #fff !important;
        border: none !important;
        transition: background-color 0.2s;
    }
    button[data-testid="baseButton-primary"]:hover,
    button[data-testid="baseButton-primaryFormSubmit"]:hover {
        background-color: #00838F !important;
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)

# --- モデル・プロフィールを取得 ---
user = st.session_state["user"]
selected_model = st.session_state.get("selected_model", "gemini-flash-latest")
profile = get_user_profile(supabase, user.id)


st.title("AI PFC Manager")

# --- 日付ナビゲーション ---
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
    f'gap:1.2rem; margin:0.2rem 0;">'
    f'<a href="?date={prev_date}" target="_self" '
    f'style="text-decoration:none; font-size:1.5rem; color:#00ACC1;">◀</a>'
    f'<span style="font-weight:bold; font-size:1.2rem;">{display_date}</span>'
    f'<a href="?date={next_date}" target="_self" '
    f'style="text-decoration:none; font-size:1.5rem; color:#00ACC1;">▶</a>'
    f'</div>',
    unsafe_allow_html=True,
)

# --- データ取得 ---
current_date_str = st.session_state.current_date.isoformat()
logs = get_meal_logs(supabase, user.id, current_date_str)

# --- 食事入力 ---
st.subheader("食事を記録")
with st.form("meal_input"):
    meal_type = st.radio("タイミング", ["朝食", "昼食", "夕食", "間食"], horizontal=True)
    food_text = st.text_area("食べたもの", height=60)
    submitted = st.form_submit_button("AI解析して記録")

    if submitted:
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

        result = analyze_meal_with_advice(
            food_text, selected_model, _profile_d,
            _logged_meals, _totals, _targets, meal_type
        )
        if result:
            p, f, c, cal, advice = result
            save_meal_log(supabase, user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)

            if advice:
                if "advice_cache" not in st.session_state:
                    st.session_state["advice_cache"] = {}
                st.session_state["advice_cache"][current_date_str] = advice
                st.session_state["advice_needs_refresh"] = False

            st.success(f"記録しました！ {cal}kcal")
            time.sleep(1)
            st.rerun()

# --- グラフ + アドバイス ---
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
st.plotly_chart(chart_fig, use_container_width=True, config={"staticPlot": True})

# --- PFCサマリー ---
totals = {"cal": total_cal, "p": total_p, "f": total_f, "c": total_c}
targets = {"cal": target_cal, "p": target_p, "f": target_f, "c": target_c}
logged_meals = logs.data if logs and logs.data else []

summary_line = generate_pfc_summary(totals, targets)
st.markdown(f"<p style='font-size:1.1rem; font-weight:bold; margin:0.2rem 0;'>{summary_line}</p>", unsafe_allow_html=True)

# --- AIアドバイス ---
if "advice_cache" not in st.session_state:
    st.session_state["advice_cache"] = {}

ADVICE_ERROR_COOLDOWN = 60
advice_error_key = "advice_error_until"
current_time = time.time()
error_until = st.session_state.get(advice_error_key, 0)

cache_key = current_date_str
needs_refresh = st.session_state.get("advice_needs_refresh", False)
has_cache = cache_key in st.session_state["advice_cache"]

advice_text = None
error_msg = None

if current_time < error_until:
    remaining = int(error_until - current_time)
    st.warning(f"⚠️ AIが混み合っています。{remaining}秒後に再試行してください。")
else:
    if needs_refresh:
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
                st.session_state["advice_cache"][cache_key] = advice_text
                st.session_state["advice_needs_refresh"] = False
                if advice_error_key in st.session_state:
                    del st.session_state[advice_error_key]
            except Exception as e:
                error_msg = str(e)
                st.session_state[advice_error_key] = current_time + ADVICE_ERROR_COOLDOWN
                st.session_state["advice_needs_refresh"] = False
                if "429" in error_msg:
                    st.warning("⚠️ AIの利用制限に達しました。日本時間の17時以降に再試行してください。")
                else:
                    st.warning("⚠️ AIアドバイスを取得できませんでした")
    elif has_cache:
        advice_text = st.session_state["advice_cache"].get(cache_key)

is_cooldown = current_time < error_until
if advice_text:
    st.subheader("💡 AIアドバイス")
    formatted = advice_text.replace("\n", "  \n")
    st.markdown(formatted)
    if st.button("🔄 アドバイスを再取得", disabled=is_cooldown, type="primary"):
        st.session_state["advice_needs_refresh"] = True
        st.rerun()
elif error_msg is None and not is_cooldown:
    if st.button("AIアドバイスを取得", type="primary"):
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

line_text = urllib.parse.quote(share_text)
st.markdown(
    f"""
    <a href="https://line.me/R/share?text={line_text}" target="_blank" style="
        display:block; width:100%; padding:0.5rem; margin-bottom:0.5rem;
        border:1px solid #06C755; border-radius:0.5rem;
        background:#06C755; color:white; text-align:center;
        text-decoration:none; font-size:0.9rem; box-sizing:border-box;
    ">LINEで共有</a>
    """,
    unsafe_allow_html=True,
)

share_text_escaped = base64.b64encode(share_text.encode()).decode()
st.markdown(
    f"""
    <button onclick="
        const text = atob('{share_text_escaped}');
        navigator.clipboard.writeText(text).then(() => {{
            this.textContent = '✅ コピーしました！';
            setTimeout(() => {{ this.textContent = 'クリップボードにコピー'; }}, 2000);
        }});
    " style="
        width:100%; padding:0.5rem; margin-bottom:0.5rem;
        border:1px solid #ccc; border-radius:0.5rem;
        background:var(--secondary-background-color);
        color:inherit; cursor:pointer; font-size:0.9rem;
    ">クリップボードにコピー</button>
    """,
    unsafe_allow_html=True,
)
