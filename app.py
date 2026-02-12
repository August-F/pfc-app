import streamlit as st
from supabase import create_client, Client
import pandas as pd
import google.generativeai as genai
import json
import time
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt # グラフ描画用にインポート追加

# 別ファイルからログイン関数をインポート
from auth import login_signup

# --- 初期設定 ---
st.set_page_config(page_title="AI PFC Manager", layout="wide")

# Supabase接続
@st.cache_resource
def init_supabase():
    # st.secretsがない場合のハンドリング（ローカル開発用など）
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
            # コンテンツ生成(generateContent)に対応しているモデルのみ抽出
            if 'generateContent' in m.supported_generation_methods:
                # 名前をきれいにする (例: models/gemini-pro -> gemini-pro)
                models.append(m.name.replace("models/", ""))
        
        # 取得できた場合はリストを返す
        if models:
            return models
    except Exception as e:
        # 取得失敗時はログを出してフォールバック
        print(f"モデル一覧取得エラー: {e}")
    
    # 取得失敗時や空の場合はデフォルトリストを返す
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
            st.error("⚠️ AIモデルの利用制限（アクセス集中、レート制限など）により解析できませんでした。時間をおくか、サイドバーから別のモデルに変更して試してください。")
        else:
            st.error(f"⚠️ AI解析エラーが発生しました: {error_msg}")
        return None

# --- メインアプリ ---
def main_app():
    user = st.session_state["user"]
    
    # --- サイドバー：設定 ---
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
        
        # 動的にモデル一覧を取得
        model_options = get_available_gemini_models()
        
        # デフォルト選択のロジック: 2.5-flashがあればそれ、なければリストの最初
        default_index = 0
        preferred_models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        
        for pref in preferred_models:
            if pref in model_options:
                default_index = model_options.index(pref)
                break

        selected_model = st.selectbox(
            "使用モデル", 
            model_options, 
            index=default_index,
            help="現在利用可能なAIモデル一覧から選択します。"
        )

        st.divider()
        # st.header("⚙️ 設定・目標") # ヘッダーを削除し、expanderのラベルにします
        
        profile = get_user_profile(user.id)
        
        # expanderで折りたたみ可能にする
        with st.expander("⚙️ 設定・目標", expanded=False):
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
                    time.sleep(0.5)
                    st.rerun()

    # --- メイン画面：日付ナビゲーション ---
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

    # --- 左カラム：食事入力 ---
    with col_input:
        st.subheader("📝 食事を記録")
        st.caption(f"{current_date_str} の記録を追加します")
        
        with st.form("meal_input"):
            meal_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"])
            food_text = st.text_area("食べたもの (例: 牛丼並盛、サラダ)", height=100)
            submitted = st.form_submit_button("AI解析して記録")
            
            if submitted:
                # 解析結果を受け取る
                result = analyze_meal_with_gemini(food_text, selected_model)
                
                # 結果がNoneでない（成功した）場合のみ保存する
                if result:
                    p, f, c, cal = result
                    save_meal_log(user.id, st.session_state.current_date, meal_type, food_text, p, f, c, cal)
                    st.success(f"記録しました！ {cal}kcal (P{p} F{f} C{c})")
                    time.sleep(1)
                    st.rerun()
                # エラーの場合は analyze_meal_with_gemini 内で st.error が表示され、保存処理はスキップされる
        
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

    # --- 右カラム：グラフと集計 ---
    with col_stats:
        st.subheader("📊 本日の進捗")
        
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
        # カスタムグラフ描画関数 (Matplotlib使用)
        # ---------------------------------------------------------
        def create_progress_chart(label, current, target, unit, base_color):
            """目標線(点線)と超過表示付きのグラフを作成"""
            fig, ax = plt.subplots(figsize=(6, 1.2))
            
            # 背景透明化
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)

            # 超過判定：目標を超えたら赤色(#FF4B4B)にする
            is_exceeded = current > target
            bar_color = base_color if not is_exceeded else "#FF4B4B"
            
            # バーの描画
            ax.barh(0, current, color=bar_color, height=0.6, align='center', zorder=3)
            
            # 目標ライン（黒い点線）を描画
            # vlines(x, ymin, ymax)
            ax.vlines(target, -0.4, 0.4, colors='black', linestyles='dashed', linewidth=2, zorder=4)
            
            # タイトル（ラベルと数値）
            ax.set_title(f"{label}: {current} / {target} {unit}", loc='left', fontsize=10, fontweight='bold', color='#333333')
            
            # 軸の装飾を消す
            ax.set_yticks([]) # Y軸ラベルなし
            for spine in ax.spines.values():
                spine.set_visible(False) # 枠線なし
            
            # X軸の範囲設定（目標値か現在値の大きい方 + 余白）
            max_val = max(current, target) * 1.15
            ax.set_xlim(0, max_val if max_val > 0 else 1)
            
            # X軸のグリッド線（薄く表示）
            ax.grid(axis='x', linestyle=':', alpha=0.5)
            
            plt.tight_layout()
            return fig

        # グラフの表示
        # カロリー: 緑
        st.pyplot(create_progress_chart("Total Calories", total_cal, target_cal, "kcal", "#4CAF50"))
        
        # P: 青
        st.pyplot(create_progress_chart("Protein (タンパク質)", total_p, target_p, "g", "#2196F3"))
        
        # F: 黄色 (脂質は注意が必要なので黄色系)
        st.pyplot(create_progress_chart("Fat (脂質)", total_f, target_f, "g", "#FFC107"))
        
        # C: ターコイズ/緑
        st.pyplot(create_progress_chart("Carb (炭水化物)", total_c, target_c, "g", "#009688"))
        
        st.divider()
        st.info("💡 AIアドバイス")
        rem_cal = target_cal - total_cal
        if rem_cal > 0:
            st.write(f"あと **{rem_cal} kcal** 食べられます。")
        else:
            st.write(f"目標カロリーを **{abs(rem_cal)} kcal** オーバーしています！")

# --- アプリ起動 ---
if "user" not in st.session_state:
    # 外部ファイルの関数を呼び出す（supabaseクライアントを渡す）
    login_signup(supabase)
else:
    main_app()
