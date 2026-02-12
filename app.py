import streamlit as st
from supabase import create_client, Client
import pandas as pd
import google.generativeai as genai
import json
import time
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt

# 別ファイルからログイン関数をインポート
from auth import login_signup

# --- 初期設定 ---
st.set_page_config(page_title="AI PFC Manager", layout="wide")

# Supabase接続
@st.cache_resource
def init_supabase():
    # st.secretsがない場合のハンドリング
    if "supabase" in st.secrets:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    return None

try:
    supabase: Client = init_supabase()
    if supabase is None:
        st.error("Supabaseの接続情報が設定されていません。secrets.tomlを確認してください。")
        st.stop()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")
    st.stop()

# Gemini接続
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

# --- セッション状態の初期化 ---
if "current_date" not in st.session_state:
    st.session_state.current_date = date.today()

# --- 関数群 (ログイン以外) ---

def get_available_gemini_models():
    """Gemini APIから利用可能なモデル一覧を取得"""
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name.replace("models/", ""))
        if models:
            return models
    except Exception as e:
        print(f"モデル一覧取得エラー: {e}")
    return ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

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

def analyze_meal_with_gemini(text, model_name="gemini-2.5-flash"):
    """GeminiでPFCとカロリーを解析"""
    if len(text) < 2: return None
    try:
        model = genai.GenerativeModel(model_name)
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
        error_msg = str(e)
        if "429" in error_msg:
            st.error("⚠️ AIモデルの利用制限（アクセス集中など）により解析できませんでした。時間を置くか、別のモデルを試してください。")
        else:
            st.error(f"⚠️ AI解析エラー: {error_msg}")
        return None

# --- メインアプリ ---
def main_app():
    user = st.session_state["user"]
    
    # --- サイドバー ---
    with st.sidebar:
        st.write(f"User: {user.email}")
        if st.button("ログアウト"):
            supabase.auth.sign_out()
            if "user" in st.session_state:
                del st.session_state["user"]
            if "session" in st.session_state:
                del st.session_state["session"]
            st.rerun()
            
        st.divider()

        st.header("🤖 AIモデル設定")
        model_options = get_available_gemini_models()
        default_index = 0
        preferred_models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        for pref in preferred_models:
            if pref in model_options:
                default_index = model_options.index(pref)
                break
        selected_model = st.selectbox("使用モデル", model_options, index=default_index)

        st.divider()
        profile = get_user_profile(user.id)
        
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
                        "likes": likes, "dislikes": dislikes, "preferences": prefs
                    }
                    update_user_profile(user.id, updates)
                    st.success("保存しました")
                    time.sleep(0.5)
                    st.rerun()

    # --- メイン画面 ---
    st.title("🍽️ AI PFC Manager")
    
    if profile.get("declaration"):
        st.info(f"🔥 **Goal: {profile.get('declaration')}**")

    col_prev, col_date, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("＜ 前日"):
            st.session_state.current_date -= timedelta(days=1)
            st.rerun()
    with col_date:
        display_date = st.session_state.current_date.strftime("%Y年 %m月 %d日 (%a)")
        st.markdown(f"<h3 style='text-align: center;'>📅 {display_date}</h3>", unsafe_allow_html=True)
    with col_next:
        if st.button("翌日 ＞"):
            st.session_state.current_date += timedelta(days=1)
            st.rerun()

    st.divider()

    col_input, col_stats = st.columns([1, 1])
    current_date_str = st.session_state.current_date.isoformat()

    # --- 左カラム：入力 ---
    with col_input:
        st.subheader("📝 食事を記録")
        with st.form("meal_input"):
            meal_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"])
            food_text = st.text_area("食べたもの", height=100)
            submitted = st.form_submit_button("AI解析して記録")
            
            if submitted:
                result = analyze_meal_with_gemini(food_text, selected_model)
                if result:
                    p, f, c, cal = result
                    save_meal_log(user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)
                    st.success(f"記録しました！ {cal}kcal")
                    time.sleep(1)
                    st.rerun()
        
        st.subheader("履歴")
        try:
            logs = supabase.table("meal_logs").select("*").eq("user_id", user.id).eq("meal_date", current_date_str).execute()
            if logs.data:
                for log in logs.data:
                    with st.expander(f"{log['meal_type']}: {log['food_name'][:15]}..."):
                        st.write(f"**{log['food_name']}**")
                        st.write(f"🔥 {log['calories']}kcal | P:{log['p_val']} F:{log['f_val']} C:{log['c_val']}")
                        if st.button("削除", key=f"del_{log['id']}"):
                            supabase.table("meal_logs").delete().eq("id", log['id']).execute()
                            st.rerun()
            else:
                st.info("まだ記録がありません")
        except Exception as e:
            st.error(f"データ取得エラー: {e}")

    # --- 右カラム：グラフ ---
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
        
        target_cal = profile.get("target_calories", 2000)
        target_p = profile.get("target_p", 100)
        target_f = profile.get("target_f", 60)
        target_c = profile.get("target_c", 250)

        # ---------------------------------------------------------
        # あすけん風 達成率比較グラフ
        # ---------------------------------------------------------
        def create_summary_chart(data_dict):
            """
            data_dict = {
                'Label': {'current': 100, 'target': 200, 'unit': 'g'},
                ...
            }
            """
            labels = list(data_dict.keys())
            # 上からカロリー、P、F、Cの順に並べたいので逆順にする（barhは下から描画するため）
            labels.reverse()
            
            # データの準備
            ratios = []
            texts = []
            colors = []
            
            for label in labels:
                d = data_dict[label]
                # ゼロ除算回避
                tgt = d['target'] if d['target'] > 0 else 1
                ratio = (d['current'] / tgt) * 100
                ratios.append(ratio)
                
                # 数値テキスト (例: 1500 / 2000 kcal)
                texts.append(f"{int(d['current'])} / {int(d['target'])} {d['unit']}")
                
                # 色分け (100%超えで赤、それ以外は緑)
                if ratio > 100:
                    colors.append("#FF4B4B") # 赤
                else:
                    colors.append("#4CAF50") # 緑 (あすけん風)

            # 描画
            fig, ax = plt.subplots(figsize=(6, 3.5))
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            
            # バーの描画
            bars = ax.barh(labels, ratios, color=colors, height=0.6, zorder=3)
            
            # 目標ライン（100%の位置）
            ax.axvline(100, color='black', linestyle='--', linewidth=1.5, zorder=4)
            
            # ラベルと数値の表示
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=11, fontweight='bold', color='#333333')
            
            # バーの右側に数値を表示
            max_ratio = max(max(ratios) if ratios else 0, 120)
            ax.set_xlim(0, max_ratio * 1.35) # テキストが入るように右側を空ける
            
            for i, bar in enumerate(bars):
                width = bar.get_width()
                label_text = texts[i]
                ax.text(width + 5, bar.get_y() + bar.get_height()/2, label_text, 
                        ha='left', va='center', fontsize=10, color='#333333')

            # X軸の設定
            ax.set_xlabel('Achievement Rate (%)', fontsize=9, color='gray')
            ax.grid(axis='x', linestyle=':', alpha=0.5)
            
            # 枠線を消す
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(left=False) # Y軸の刻みを消す
            
            plt.tight_layout()
            return fig

        # データ作成
        chart_data = {
            "Calories": {"current": total_cal, "target": target_cal, "unit": "kcal"},
            "Protein":  {"current": total_p,   "target": target_p,   "unit": "g"},
            "Fat":      {"current": total_f,   "target": target_f,   "unit": "g"},
            "Carb":     {"current": total_c,   "target": target_c,   "unit": "g"}
        }
        
        # グラフ描画
        st.pyplot(create_summary_chart(chart_data))

        # アドバイス
        st.divider()
        st.info("💡 AIアドバイス")
        rem_cal = target_cal - total_cal
        if rem_cal > 0:
            st.write(f"あと **{rem_cal} kcal** 食べられます。")
        else:
            st.write(f"目標カロリーを **{abs(rem_cal)} kcal** オーバーしています！")

# --- アプリ起動 ---
if "user" not in st.session_state:
    login_signup(supabase)
else:
    main_app()
