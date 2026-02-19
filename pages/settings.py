"""
⚙️ 設定ページ（AIモデル + 目標・好み）
"""

import streamlit as st
import time

from config import get_supabase
from services import get_available_gemini_models, get_user_profile, update_user_profile

supabase = get_supabase()

DEFAULT_USER_ID = "d8875444-a88a-4a31-947d-2174eefb80f0"

if "user" in st.session_state:
    user_id = st.session_state["user"].id
else:
    user_id = DEFAULT_USER_ID

profile = get_user_profile(user_id)

st.title("⚙️ 設定")

st.markdown("""
<style>
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child {
        background-color: white !important;
        color: #31333F !important;
    }
    [data-testid="stFormSubmitButton"] > button {
        background-color: white !important;
        color: #31333F !important;
        border-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# AIモデル設定
# =========================================================
st.subheader("🤖 AIモデル設定")
st.caption("食事解析・アドバイスに使用するGeminiモデルを選択します")

model_options = get_available_gemini_models()
current_model = st.session_state.get("selected_model", "gemini-flash-latest")

if current_model in model_options:
    default_index = model_options.index(current_model)
else:
    default_index = 0
    for pref in ["gemini-flash-latest", "gemini-3-flash", "gemini-2.5-flash"]:
        if pref in model_options:
            default_index = model_options.index(pref)
            break

selected = st.selectbox("使用モデル", model_options, index=default_index)

if selected != current_model:
    st.session_state["selected_model"] = selected
    st.success(f"✅ モデルを **{selected}** に変更しました")

st.divider()

# =========================================================
# 目標・好み設定
# =========================================================
st.subheader("🎯 目標・好み設定")
st.caption("カロリー・PFCの目標値や食事の好みを設定します")

with st.form("profile_form"):
    # --- 目標数値 ---
    st.markdown("**目標数値**")

    col1, col2 = st.columns(2)
    with col1:
        t_cal = st.number_input(
            "目標カロリー (kcal)",
            value=profile.get("target_calories", 2000),
            min_value=0, step=50,
        )
        t_p = st.number_input(
            "目標タンパク質 P (g)",
            value=profile.get("target_p", 100),
            min_value=0, step=5,
        )
    with col2:
        t_f = st.number_input(
            "目標脂質 F (g)",
            value=profile.get("target_f", 60),
            min_value=0, step=5,
        )
        t_c = st.number_input(
            "目標炭水化物 C (g)",
            value=profile.get("target_c", 250),
            min_value=0, step=5,
        )

    # PFCバランスのプレビュー
    total_cal_from_pfc = t_p * 4 + t_f * 9 + t_c * 4
    if total_cal_from_pfc > 0:
        p_pct = round(t_p * 4 / total_cal_from_pfc * 100)
        f_pct = round(t_f * 9 / total_cal_from_pfc * 100)
        c_pct = 100 - p_pct - f_pct
        st.markdown(
            f"<div style='background:rgba(0,172,193,0.08); border-radius:8px; padding:10px 14px; "
            f"font-size:0.85rem; margin:8px 0;'>"
            f"📊 PFC比率プレビュー: "
            f"<b style='color:#3B82F6;'>P {p_pct}%</b> · "
            f"<b style='color:#EAB308;'>F {f_pct}%</b> · "
            f"<b style='color:#22C55E;'>C {c_pct}%</b>"
            f"（合計 {total_cal_from_pfc:,} kcal）"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("")  # スペーサー

    # --- 好み・要望 ---
    st.markdown("**好み・要望**")
    st.caption("AIアドバイスの提案内容に反映されます")

    likes = st.text_area(
        "好きな食べ物",
        value=profile.get("likes") or "",
        placeholder="例: 鶏むね肉、サラダ、和食",
    )
    dislikes = st.text_area(
        "苦手な食べ物",
        value=profile.get("dislikes") or "",
        placeholder="例: レバー、セロリ",
    )
    prefs = st.text_area(
        "その他要望",
        value=profile.get("preferences") or "",
        placeholder="例: コンビニで買えるもの中心、作り置きOK",
    )

    if st.form_submit_button("💾 設定を保存", use_container_width=True):
        updates = {
            "target_calories": t_cal,
            "target_p": t_p, "target_f": t_f, "target_c": t_c,
            "likes": likes, "dislikes": dislikes, "preferences": prefs,
        }
        update_user_profile(supabase, user_id, updates)
        st.success("✅ 設定を保存しました！")
        time.sleep(1)
        st.rerun()
