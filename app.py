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
    get_available_gemini_models, analyze_meal_with_gemini,
    get_user_profile, update_user_profile,
    save_meal_log, get_meal_logs, delete_meal_log,
    generate_meal_advice,
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
        padding: 0.5rem !important;
    }
    /* 数値入力の調整 */
    div[data-baseweb="input"] > div {
        padding: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 初期化 ---
supabase = get_supabase()
init_gemini()

# --- セッション管理 (簡易版: 常にダミーユーザー) ---
if "user" not in st.session_state:
    # 開発用ダミーユーザー
    st.session_state["user"] = {"id": "dummy-user-id", "email": "test@example.com"}

user = st.session_state["user"]
user_id = user["id"]

# --- サイドバー設定 ---
with st.sidebar:
    st.title("⚙️ 設定")
    
    # モデル選択（キャッシュ化された関数を使用）
    available_models = get_available_gemini_models()
    selected_model = st.selectbox("使用AIモデル", available_models, index=0)

    st.markdown("---")
    st.subheader("👤 目標設定")
    
    # プロフィール取得
    profile = get_user_profile(supabase, user_id)
    
    # デフォルト値
    default_cal = profile.get("target_calories", 2000)
    default_p = profile.get("target_p", 100)
    default_f = profile.get("target_f", 60)
    default_c = profile.get("target_c", 250)

    with st.form("target_form"):
        target_cal = st.number_input("目標カロリー (kcal)", value=default_cal, step=50)
        col1, col2, col3 = st.columns(3)
        with col1:
            target_p = st.number_input("P (g)", value=default_p, step=5)
        with col2:
            target_f = st.number_input("F (g)", value=default_f, step=5)
        with col3:
            target_c = st.number_input("C (g)", value=default_c, step=5)
            
        if st.form_submit_button("保存"):
            update_user_profile(supabase, user_id, {
                "target_calories": target_cal,
                "target_p": target_p,
                "target_f": target_f,
                "target_c": target_c
            })
            st.success("目標を更新しました！")
            time.sleep(1)
            st.rerun()

# --- メイン画面 ---
st.title("🍽️ AI PFC Manager")

# 日付選択
if "current_date" not in st.session_state:
    st.session_state["current_date"] = date.today()

col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
with col_d1:
    if st.button("◀ 前日"):
        st.session_state["current_date"] -= timedelta(days=1)
        st.rerun()
with col_d2:
    st.markdown(f"<h3 style='text-align: center; margin:0;'>{st.session_state['current_date']}</h3>", unsafe_allow_html=True)
with col_d3:
    if st.button("翌日 ▶"):
        st.session_state["current_date"] += timedelta(days=1)
        st.rerun()

current_date_str = st.session_state["current_date"].isoformat()

# --- 食事記録フォーム ---
st.subheader("📝 食事記録")
with st.form("meal_input_form", clear_on_submit=True):
    meal_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"], index=1)
    meal_text = st.text_area("食事内容を入力（例: 牛丼大盛りとサラダ）", height=80)
    
    submitted = st.form_submit_button("AIで解析・記録 🚀")
    
    if submitted and meal_text:
        with st.spinner("AIが栄養素を計算中..."):
            result = analyze_meal_with_gemini(meal_text, selected_model)
            if result:
                save_meal_log(
                    supabase, user_id, st.session_state["current_date"],
                    meal_type, meal_text,
                    result["p"], result["f"], result["c"], result["cal"]
                )
                st.success(f"記録しました！ (Cal: {result['cal']}kcal, P: {result['p']}g, F: {result['f']}g, C: {result['c']}g)")
                time.sleep(1)
                st.rerun()
            else:
                st.error("解析に失敗しました。もう少し詳しく入力してください。")

# --- 今日のサマリー表示 ---
meal_logs = get_meal_logs(supabase, user_id, current_date_str)

# 集計
totals = {"calories": 0, "p_val": 0, "f_val": 0, "c_val": 0}
for log in meal_logs:
    totals["calories"] += log["calories"]
    totals["p_val"] += log["p_val"]
    totals["f_val"] += log["f_val"]
    totals["c_val"] += log["c_val"]

# 目標値（サイドバーの設定値を使用）
targets = {
    "cal": target_cal, "p": target_p, "f": target_f, "c": target_c
}

st.markdown("---")
st.subheader("📊 本日の達成状況")

# グラフ用データ作成
chart_data = {
    'Calories': {'current': totals["calories"], 'target': targets["cal"], 'unit': 'kcal'},
    'Protein':  {'current': totals["p_val"],    'target': targets["p"],   'unit': 'g'},
    'Fat':      {'current': totals["f_val"],    'target': targets["f"],   'unit': 'g'},
    'Carbs':    {'current': totals["c_val"],    'target': targets["c"],   'unit': 'g'},
}

# グラフ描画
fig = create_summary_chart(chart_data)
st.pyplot(fig, use_container_width=True)


# --- 履歴一覧 ---
with st.expander("📅 食事履歴を確認・削除", expanded=False):
    if not meal_logs:
        st.info("まだ記録がありません。")
    else:
        for log in meal_logs:
            col_l1, col_l2 = st.columns([4, 1])
            with col_l1:
                st.markdown(f"**[{log['meal_type']}]** {log['food_name']}")
                st.caption(f"🔥 {log['calories']}kcal | P:{log['p_val']}g F:{log['f_val']}g C:{log['c_val']}g")
            with col_l2:
                if st.button("削除", key=f"del_{log['id']}"):
                    delete_meal_log(supabase, log['id'])
                    st.rerun()

st.markdown("---")

# --- AIアドバイス (修正版: ボタン式に変更) ---
st.subheader("💡 AIトレーナーからのアドバイス")

# 以前はここで自動的に generate_meal_advice を呼んでいたため、
# 画面描画のたびにAPIを消費し、エラー時も再試行ループが発生していました。
# ボタンを押したときだけ実行するように変更します。

if st.button("AIアドバイスをもらう"):
    with st.spinner("🏋️ AIがアドバイスを生成中..."):
        try:
            # キャッシュが効くので、短時間に連打してもAPI消費は1回で済みます
            advice_text = generate_meal_advice(
                selected_model,
                profile,
                meal_logs,
                totals,
                targets
            )
            # 改行コードをマークダウン用に調整
            formatted_advice = advice_text.replace("\n", "  \n")
            
            # アドバイスを表示
            st.success("受信完了！")
            st.markdown(formatted_advice)
            
        except Exception as e:
            st.warning(f"取得できませんでした: {e}")
else:
    st.info("ボタンを押すと、今日の食事内容に基づいたアドバイスを表示します（API節約モード）")


# --- 共有機能 ---
with st.expander("📤 今日の結果をシェア"):
    share_text = f"""【{current_date_str}の食事記録】
カロリー: {totals['calories']}/{targets['cal']} kcal
P: {totals['p_val']}/{targets['p']} g
F: {totals['f_val']}/{targets['f']} g
C: {totals['c_val']}/{targets['c']} g
#AI_PFC_Manager"""
    
    st.text_area("コピー用テキスト", share_text, height=100)
    
    # LINE共有リンク
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
        unsafe_allow_html=True
    )
