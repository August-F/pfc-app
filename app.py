import streamlit as st
from supabase import create_client, Client
import pandas as pd
import google.generativeai as genai
import json
import time
from datetime import datetime, timedelta, date

# --- 初期設定 ---
st.set_page_config(page_title="AI PFC Manager", layout="wide")

# Supabase接続
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")
    st.stop()

# Gemini接続
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

# --- セッション状態の初期化 ---
if "current_date" not in st.session_state:
    st.session_state.current_date = date.today()

# --- 関数群 ---

def login_signup():
    """ログイン・サインアップ画面"""
    st.title("🔐 AI PFC Manager ログイン")
    
    tab1, tab2 = st.tabs(["ログイン", "新規登録"])
    
    with tab1:
        email = st.text_input("メールアドレス", key="login_email")
        password = st.text_input("パスワード", type="password", key="login_pass")
        if st.button("ログイン"):
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["user"] = response.user
                st.session_state["session"] = response.session
                st.success("ログイン成功")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"ログイン失敗: {e}")

    with tab2:
        st.caption("登録後、自動ログインします（メール確認OFFの場合）")
        new_email = st.text_input("メールアドレス", key="signup_email")
        new_password = st.text_input("パスワード", type="password", key="signup_pass")
        if st.button("アカウント作成"):
            try:
                response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("登録完了！ログインしてください。")
            except Exception as e:
                st.error(f"登録エラー: {e}")

def get_user_profile(user_id):
    """ユーザー設定を取得"""
    try:
        data = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if data.data:
            return data.data[0]
        return {}
    except:
        return {}

def update_user_profile(user_id, updates):
    """ユーザー設定を更新"""
    supabase.table("profiles").update(updates).eq("id", user_id).execute()

def save_meal_log(user_id, meal_date, meal_type, text, p, f, c, cal):
    """食事ログをDBに保存"""
    supabase.table("meal_logs").insert({
        "user_id": user_id,
        "meal_date": meal_date.isoformat(),
        "meal_type": meal_type,
        "food_name": text,
        "p_val": p, "f_val": f, "c_val": c, "calories": cal
    }).execute()

def analyze_meal_with_gemini(text):
    """GeminiでPFCとカロリーを解析"""
    if len(text) < 2: return 0, 0, 0, 0
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        # プロンプト：カロリーも含めるように指示
        prompt = f"""
        あなたは栄養管理AIです。以下の食事内容から、カロリー、タンパク質(P)、脂質(F)、炭水化物(C)を推測してください。
        
        食事内容: "{text}"
        
        回答は以下のJSON形式のみで出力してください（マークダウン不要）:
        {{"cal": int, "p": int, "f": int, "c": int}}
        例: {{"cal": 500, "p": 20, "f": 15, "c": 60}}
        """
        res = model.generate_content(prompt)
        json_str = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_str)
        return data.get("p", 0), data.get("f", 0), data.get("c", 0), data.get("cal", 0)
    except Exception as e:
        st.error(f"AI解析エラー: {e}")
        return 0, 0, 0, 0

# --- メインアプリ ---
def main_app():
    user = st.session_state["user"]
    
    # --- サイドバー：プロフィール設定 ---
    with st.sidebar:
        st.write(f"User: {user.email}")
        if st.button("ログアウト"):
            supabase.auth.sign_out()
            del st.session_state["user"]
            st.rerun()
            
        st.divider()
        st.header("⚙️ 設定・目標")
        
        profile = get_user_profile(user.id)
        
        with st.form("profile_form"):
            decl = st.text_input("🔥 宣言 (My Goal)", value=profile.get("declaration") or "")
            
            st.subheader("目標数値")
            t_cal = st.number_input("目標カロリー (kcal)", value=profile.get("target_calories", 2000))
            t_p = st.number_input("目標 P (g)", value=profile.get("target_p", 100))
            t_f = st.number_input("目標 F (g)", value=profile.get("target_f", 60))
            t_c = st.number_input("目標 C (g)", value=profile.get("target_c", 250))
            
            st.subheader("好み・要望")
            likes = st.text_area("好きな食べ物", value=profile.get("likes") or "")
            dislikes = st.text_area("苦手な食べ物", value=profile.get("dislikes") or "")
            prefs = st.text_area("その他要望 (調理など)", value=profile.get("preferences") or "")
            
            if st.form_submit_button("設定を保存"):
                updates = {
                    "declaration": decl,
                    "target_calories": t_cal,
                    "target_p": t_p, "target_f": t_f, "target_c": t_c,
                    "likes": likes, "dislikes": dislikes, "preferences": prefs
                }
                update_user_profile(user.id, updates)
                st.success("保存しました")
                st.rerun()

    # --- メイン画面：日付ナビゲーション ---
    st.title("🍽️ AI PFC Manager")
    
    # 宣言の表示
    if profile.get("declaration"):
        st.info(f"🔥 **Goal:** {profile.get('declaration')}")

    # 日付切り替えボタン
    col_prev, col_date, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("＜ 前日"):
            st.session_state.current_date -= timedelta(days=1)
            st.rerun()
    with col_date:
        # 日付を大きく表示
        display_date = st.session_state.current_date.strftime("%Y年 %m月 %d日 (%a)")
        st.markdown(f"<h3 style='text-align: center;'>📅 {display_date}</h3>", unsafe_allow_html=True)
    with col_next:
        if st.button("翌日 ＞"):
            st.session_state.current_date += timedelta(days=1)
            st.rerun()

    st.divider()

    # --- 2カラムレイアウト ---
    col_input, col_stats = st.columns([1, 1])
    
    # 現在選択されている日付を取得
    current_date_str = st.session_state.current_date.isoformat()

    # --- 左カラム：食事入力 ---
    with col_input:
        st.subheader("📝 食事を記録")
        st.caption(f"{current_date_str} の記録を追加します")
        
        with st.form("meal_input"):
            meal_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"])
            food_text = st.text_area("食べたもの (例: 牛丼並盛、サラダ)", height=100)
            submitted = st.form_submit_button("AI解析して記録")
            
            if submitted:
                p, f, c, cal = analyze_meal_with_gemini(food_text)
                save_meal_log(user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)
                st.success(f"記録しました！ {cal}kcal (P{p} F{f} C{c})")
                time.sleep(1)
                st.rerun()
        
        # 今日の食事履歴リスト
        st.subheader("履歴")
        logs = supabase.table("meal_logs").select("*").eq("user_id", user.id).eq("meal_date", current_date_str).execute()
        
        if logs.data:
            for log in logs.data:
                with st.expander(f"{log['meal_type']}: {log['food_name'][:15]}..."):
                    st.write(f"**{log['food_name']}**")
                    st.write(f"🔥 {log['calories']}kcal | P:{log['p_val']} F:{log['f_val']} C:{log['c_val']}")
                    # 削除ボタンの実装（IDを指定して削除）
                    if st.button("削除", key=f"del_{log['id']}"):
                        supabase.table("meal_logs").delete().eq("id", log['id']).execute()
                        st.rerun()

    # --- 右カラム：グラフと集計 ---
    with col_stats:
        st.subheader("📊 本日の進捗")
        
        # 集計
        total_p = total_f = total_c = total_cal = 0
        if logs.data:
            df = pd.DataFrame(logs.data)
            total_p = df["p_val"].sum()
            total_f = df["f_val"].sum()
            total_c = df["c_val"].sum()
            total_cal = df["calories"].sum()
        
        # 目標値の取得
        target_cal = profile.get("target_calories", 2000)
        target_p = profile.get("target_p", 100)
        target_f = profile.get("target_f", 60)
        target_c = profile.get("target_c", 250)

        # カロリーメーター
        st.write(f"**Total Calories: {total_cal} / {target_cal} kcal**")
        st.progress(min(total_cal / target_cal, 1.0))

        # PFCメーター関数
        def pfc_meter(label, current, target, color):
            st.write(f"**{label}: {current} / {target} g**")
            st.progress(min(current / target, 1.0))
        
        pfc_meter("Protein (タンパク質)", total_p, target_p, "red")
        pfc_meter("Fat (脂質)", total_f, target_f, "yellow")
        pfc_meter("Carb (炭水化物)", total_c, target_c, "green")
        
        # アドバイス表示 (簡易版)
        st.divider()
        st.info("💡 AIアドバイス")
        rem_cal = target_cal - total_cal
        if rem_cal > 0:
            st.write(f"あと **{rem_cal} kcal** 食べられます。")
        else:
            st.write(f"目標カロリーを **{abs(rem_cal)} kcal** オーバーしています！")

# --- アプリ起動 ---
if "user" not in st.session_state:
    login_signup()
else:
    main_app()
