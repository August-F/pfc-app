"""
🍽️ 食事記録ページ
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import base64
import urllib.parse
from datetime import timedelta, date

from config import get_supabase
from services import (
    analyze_meal_with_gemini,
    get_user_profile,
    save_meal_log, get_meal_logs, delete_meal_log,
    # generate_meal_advice,  # アドバイス機能を一時無効化
    generate_pfc_summary,
    get_meal_templates, delete_meal_template,
)
from charts import create_summary_chart

supabase = get_supabase()

# --- ページ固有の余白縮小CSS ---
st.markdown("""
<style>
    .block-container h2 { margin-top: 0.4rem !important; margin-bottom: 0.2rem !important; }
    .block-container h3 { margin-top: 0.3rem !important; margin-bottom: 0.1rem !important; }
    .block-container hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
    .streamlit-expanderHeader { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; }
    [data-testid="stFormSubmitButton"] > button {
        background-color: white !important;
        color: #31333F !important;
        border-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# --- モデル・プロフィールを取得 ---
if "user" not in st.session_state:
    st.session_state["user"] = type("_DefaultUser", (), {
        "id": "d8875444-a88a-4a31-947d-2174eefb80f0",
        "email": "guest@example.com",
    })()
user = st.session_state["user"]
selected_model = st.session_state.get("selected_model", "gemini-flash-latest")
profile = get_user_profile(user.id)


st.title("AI PFC Manager")

# --- 日付ナビゲーション ---
params = st.query_params
if "date" in params:
    try:
        st.session_state.current_date = date.fromisoformat(params["date"])
    except ValueError:
        pass

# --- 週カレンダービュー ---
current_date = st.session_state.current_date
today = date.today()

week_days = [current_date + timedelta(days=i - 3) for i in range(7)]

display_date_large = f"{current_date.year}.{current_date.month}.{current_date.day}"

DAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]
day_cells_html = ""
for d in week_days:
    is_selected = (d == current_date)
    is_sunday = (d.weekday() == 6)
    is_today_cell = (d == today)
    date_str = d.isoformat()
    day_num = d.day
    day_name = "今日" if is_today_cell else DAY_NAMES[d.weekday()]
    name_color = "#FF3B30" if is_sunday else "inherit"

    if is_selected:
        day_cells_html += (
            f'<div class="day-cell day-cell--active">'
            f'<span class="day-name" style="color:{name_color};">{day_name}</span>'
            f'<span class="day-num">{day_num}</span>'
            f'</div>'
        )
    else:
        day_cells_html += (
            f'<a href="?date={date_str}" target="_self" class="day-cell">'
            f'<span class="day-name" style="color:{name_color};">{day_name}</span>'
            f'<span class="day-num">{day_num}</span>'
            f'</a>'
        )

st.markdown(f"""
<style>
    .week-header {{ text-align:center; margin:0.3rem 0 0.6rem 0; }}
    .week-date-large {{ font-size:1.8rem; font-weight:700; margin-bottom:0.6rem; display:block; }}
    .week-strip {{ display:flex; justify-content:space-around; align-items:center; }}
    .day-cell {{
        display:flex; flex-direction:column; align-items:center;
        padding:0.3rem 0.6rem; border-radius:0.7rem;
        text-decoration:none !important; color:inherit; gap:0.1rem; min-width:2rem;
    }}
    a.day-cell, a.day-cell:hover, a.day-cell:visited {{
        text-decoration:none !important;
    }}
    .day-cell--active {{ background:rgba(0,172,193,0.18); }}
    .day-name {{ font-size:0.75rem; }}
    .day-num {{ font-size:1.05rem; font-weight:700; }}
    @media (prefers-color-scheme: dark) {{
        .day-cell--active {{ background:rgba(0,172,193,0.28); }}
    }}
</style>
<div class="week-header">
    <span class="week-date-large">{display_date_large}</span>
    <div class="week-strip">{day_cells_html}</div>
</div>
""", unsafe_allow_html=True)

# --- データ取得 ---
current_date_str = st.session_state.current_date.isoformat()
logs = get_meal_logs(supabase, user.id, current_date_str)

# --- 食事入力 ---
st.subheader("食事を記録")

# ── テンプレートから登録 ──────────────────────────────────
templates = get_meal_templates(supabase, user.id)

with st.expander("📋 テンプレートから登録"):
    if templates:
        template_names = [t["name"] for t in templates]
        selected_name = st.selectbox("テンプレートを選択", template_names, key="tpl_select")
        tpl = next(t for t in templates if t["name"] == selected_name)

        st.caption(
            f"{tpl['food_name']}　"
            f"{tpl['calories']:.0f}kcal　"
            f"P:{tpl['p_val']:.1f}g　F:{tpl['f_val']:.1f}g　C:{tpl['c_val']:.1f}g"
        )

        tpl_meal_type = st.radio(
            "食事タイプ",
            ["朝食", "昼食", "夕食", "間食"],
            index=["朝食", "昼食", "夕食", "間食"].index(tpl["meal_type"])
                  if tpl.get("meal_type") in ["朝食", "昼食", "夕食", "間食"] else 0,
            horizontal=True,
            key="tpl_meal_type",
        )

        if st.button("✅ このテンプレートで登録", use_container_width=True, key="tpl_register"):
            save_meal_log(
                supabase, user.id,
                st.session_state.current_date,
                tpl_meal_type,
                tpl["food_name"],
                tpl["p_val"], tpl["f_val"], tpl["c_val"], tpl["calories"],
            )
            # st.session_state["advice_needs_refresh"] = True  # アドバイス機能を一時無効化
            st.toast(f"✅ {tpl['name']} を登録しました！")
            st.rerun()
    else:
        st.info("テンプレートがまだありません。設定ページから追加できます。")

with st.form("meal_input"):
    meal_type = st.radio("タイミング", ["朝食", "昼食", "夕食", "間食"], horizontal=True)
    food_text = st.text_area("食べたもの", height=60)
    submitted = st.form_submit_button("AI解析して記録")

    if submitted:
        result = analyze_meal_with_gemini(food_text, selected_model)
        if result:
            p, f, c, cal, iron, folate, calcium, vit_d = result
            save_meal_log(supabase, user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal,
                          iron_mg=iron, folate_ug=folate, calcium_mg=calcium, vitamin_d_ug=vit_d)
            # st.session_state["advice_needs_refresh"] = True  # アドバイス機能を一時無効化
            st.toast(f"✅ 記録しました！ {cal}kcal")
            st.rerun()

# --- グラフ + アドバイス ---
total_p = total_f = total_c = total_cal = 0
total_iron = total_folate = total_calcium = total_vit_d = 0.0
if logs and logs.data:
    df = pd.DataFrame(logs.data)
    total_p = df["p_val"].sum()
    total_f = df["f_val"].sum()
    total_c = df["c_val"].sum()
    total_cal = df["calories"].sum()
    total_iron   = df["iron_mg"].fillna(0).sum()   if "iron_mg"    in df.columns else 0.0
    total_folate = df["folate_ug"].fillna(0).sum() if "folate_ug"   in df.columns else 0.0
    total_calcium= df["calcium_mg"].fillna(0).sum()if "calcium_mg"  in df.columns else 0.0
    total_vit_d  = df["vitamin_d_ug"].fillna(0).sum() if "vitamin_d_ug" in df.columns else 0.0

target_cal = profile.get("target_calories") or 2000
target_p   = profile.get("target_p") or 100
target_f   = profile.get("target_f") or 60
target_c   = profile.get("target_c") or 250

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

# --- 微量栄養素サマリー ---
MICRO_TARGETS = {"iron": 10.5, "folate": 240.0, "calcium": 650.0, "vit_d": 8.5}
micro_items = [
    ("鉄",      total_iron,    MICRO_TARGETS["iron"],    "mg"),
    ("葉酸",    total_folate,  MICRO_TARGETS["folate"],  "µg"),
    ("カルシウム", total_calcium, MICRO_TARGETS["calcium"], "mg"),
    ("ビタミンD",  total_vit_d,   MICRO_TARGETS["vit_d"],   "µg"),
]

def _micro_color(current, target):
    ratio = current / target if target else 0
    if ratio >= 0.8:
        return "#4caf50"
    elif ratio >= 0.5:
        return "#ff9800"
    else:
        return "#9e9e9e"

micro_html = "<div style='display:flex; flex-wrap:nowrap; gap:0.5rem; justify-content:space-between; overflow-x:auto;'>"
for label, cur, tgt, unit in micro_items:
    color = _micro_color(cur, tgt)
    micro_html += (
        f"<div style='flex:1; min-width:3.5rem; text-align:center;'>"
        f"<div style='font-size:0.75rem; color:#888; white-space:nowrap;'>{label}</div>"
        f"<div style='font-size:1rem; font-weight:bold; color:{color};'>{cur:.1f}</div>"
        f"<div style='font-size:0.7rem; color:#aaa; white-space:nowrap;'>/{tgt}{unit}</div>"
        f"</div>"
    )
micro_html += "</div>"
st.markdown(micro_html, unsafe_allow_html=True)

# --- AIアドバイス（一時無効化） ---
# if "advice_cache" not in st.session_state:
#     st.session_state["advice_cache"] = {}
#
# ADVICE_ERROR_COOLDOWN = 60
# advice_error_key = "advice_error_until"
# current_time = time.time()
# error_until = st.session_state.get(advice_error_key, 0)
#
# cache_key = current_date_str
# needs_refresh = st.session_state.get("advice_needs_refresh", False)
# has_cache = cache_key in st.session_state["advice_cache"]
#
# advice_text = None
# error_msg = None
#
# if current_time < error_until:
#     remaining = int(error_until - current_time)
#     st.warning(f"⚠️ AIが混み合っています。{remaining}秒後に再試行してください。")
# else:
#     if needs_refresh:
#         with st.spinner("🏋️ アドバイスを考え中..."):
#             try:
#                 profile_d = {
#                     "likes": profile.get("likes") or "",
#                     "dislikes": profile.get("dislikes") or "",
#                     "preferences": profile.get("preferences") or "",
#                 }
#                 advice_text = generate_meal_advice(
#                     selected_model, profile_d, logged_meals, totals, targets
#                 )
#                 st.session_state["advice_cache"][cache_key] = advice_text
#                 st.session_state["advice_needs_refresh"] = False
#                 if advice_error_key in st.session_state:
#                     del st.session_state[advice_error_key]
#             except Exception as e:
#                 error_msg = str(e)
#                 st.session_state[advice_error_key] = current_time + ADVICE_ERROR_COOLDOWN
#                 st.session_state["advice_needs_refresh"] = False
#                 if "429" in error_msg:
#                     st.warning("⚠️ AIの利用制限に達しました。日本時間の17時以降に再試行してください。")
#                 else:
#                     st.warning("⚠️ AIアドバイスを取得できませんでした")
#     elif has_cache:
#         advice_text = st.session_state["advice_cache"].get(cache_key)
#
# is_cooldown = current_time < error_until
# if advice_text:
#     st.subheader("💡 AIアドバイス")
#     formatted = advice_text.replace("\n", "  \n")
#     st.markdown(formatted)
#     if st.button("🔄 アドバイスを再取得", disabled=is_cooldown):
#         st.session_state["advice_needs_refresh"] = True
#         st.rerun()
# elif error_msg is None and not is_cooldown:
#     if st.button("AIアドバイスを取得"):
#         st.session_state["advice_needs_refresh"] = True
#         st.rerun()

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

share_lines = [f"🍽️ {display_date_large} の食事記録"]
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
share_text_escaped = base64.b64encode(share_text.encode()).decode()
gemini_text = share_text + "\n\nこのあとの食事を提案してください。"
gemini_text_escaped = base64.b64encode(gemini_text.encode()).decode()
components.html(
    f"""
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; }}
        .btn {{
            display: block; width: 100%; padding: 0.5rem; margin-bottom: 0.5rem;
            border-radius: 0.5rem; font-size: 0.9rem; box-sizing: border-box;
            text-align: center; cursor: pointer; text-decoration: none;
            font-family: sans-serif;
        }}
        .btn-line {{
            border: 1px solid #06C755; background: #06C755; color: white;
        }}
        .btn-copy {{
            border: 1px solid #ccc; background: #f0f2f6; color: #31333f;
        }}
        .btn-gemini {{
            border: 1px solid #1a73e8; background: #1a73e8; color: white;
        }}
        @media (prefers-color-scheme: dark) {{
            .btn-copy {{ background: #262730; color: #fafafa; border-color: #555; }}
        }}
    </style>
    <a href="https://line.me/R/share?text={line_text}" target="_blank" class="btn btn-line">LINEで共有</a>
    <button id="geminiBtn" class="btn btn-gemini" onclick="
        const bytes = Uint8Array.from(atob('{gemini_text_escaped}'), c => c.charCodeAt(0));
        const text = new TextDecoder().decode(bytes);
        const btn = document.getElementById('geminiBtn');
        const label = '✨ Geminiに相談';
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(text).then(() => {{
                btn.textContent = '✅ コピーしました！貼り付けてください';
                window.open('https://gemini.google.com/app', '_blank');
                setTimeout(() => {{ btn.textContent = label; }}, 3000);
            }}).catch(() => {{ fallbackGemini(text, btn, label); }});
        }} else {{
            fallbackGemini(text, btn, label);
        }}
        function fallbackGemini(text, btn, label) {{
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try {{
                document.execCommand('copy');
                btn.textContent = '✅ コピーしました！貼り付けてください';
                window.open('https://gemini.google.com/app', '_blank');
                setTimeout(() => {{ btn.textContent = label; }}, 3000);
            }} catch (e) {{
                btn.textContent = '❌ コピー失敗';
                setTimeout(() => {{ btn.textContent = label; }}, 2000);
            }}
            document.body.removeChild(ta);
        }}
    ">✨ Geminiに相談</button>
    <button id="copyBtn" class="btn btn-copy" onclick="
        const bytes = Uint8Array.from(atob('{share_text_escaped}'), c => c.charCodeAt(0));
        const text = new TextDecoder().decode(bytes);
        const btn = document.getElementById('copyBtn');
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(text).then(() => {{
                btn.textContent = '✅ コピーしました！';
                setTimeout(() => {{ btn.textContent = 'クリップボードにコピー'; }}, 2000);
            }}).catch(() => {{ fallbackCopy(text, btn, 'クリップボードにコピー'); }});
        }} else {{
            fallbackCopy(text, btn, 'クリップボードにコピー');
        }}
        function fallbackCopy(text, btn, label) {{
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try {{
                document.execCommand('copy');
                btn.textContent = '✅ コピーしました！';
                setTimeout(() => {{ btn.textContent = label; }}, 2000);
            }} catch (e) {{
                btn.textContent = '❌ コピー失敗';
                setTimeout(() => {{ btn.textContent = label; }}, 2000);
            }}
            document.body.removeChild(ta);
        }}
    ">クリップボードにコピー</button>
    """,
    height=130,
)
