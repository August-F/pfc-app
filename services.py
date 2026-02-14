import streamlit as st
import google.generativeai as genai
import json


# --- Gemini関連 ---

@st.cache_data(ttl=86400)  # 1日キャッシュしてAPI呼び出しを節約
def get_available_gemini_models():
    """Gemini APIから利用可能なモデル一覧を取得"""
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                models.append(name)
        if models:
            return models
    except Exception as e:
        print(f"モデル一覧取得エラー: {e}")
    # 取得失敗時のフォールバック
    return ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]


def analyze_meal_with_gemini(text, model_name="gemini-2.5-flash"):
    """GeminiでPFCとカロリーを解析"""
    if len(text) < 2:
        return None
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
        # JSON部分だけ抽出（念のため）
        cleaned_text = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None


@st.cache_data(ttl=3600)  # アドバイスは1時間キャッシュ（同じデータならAPIを叩かない）
def generate_meal_advice(model_name, profile_data, meal_logs, daily_totals, targets):
    """
    一日の食事データとプロフィールから、マッチョなトレーナー風のアドバイスを生成
    """
    # ログが空ならアドバイス不要
    if not meal_logs:
        return "まだ食事が記録されてないな！しっかり食べて筋肉を育てようぜ！💪"

    # プロンプト作成
    prompt = f"""
    あなたは熱血でポジティブなパーソナルトレーナーAIです。
    ユーザーの今日の食事内容と目標達成度を見て、短いアドバイス（3行程度）をください。
    語尾は「だぜ！」「筋肉が喜んでるぞ！」「ナイスバルク！」など、マッチョで元気な口調でお願いします。

    【ユーザー目標】
    カロリー: {targets['cal']}kcal, P: {targets['p']}g, F: {targets['f']}g, C: {targets['c']}g

    【今日の摂取合計】
    カロリー: {daily_totals['calories']}kcal
    P: {daily_totals['p_val']}g
    F: {daily_totals['f_val']}g
    C: {daily_totals['c_val']}g

    【食べたものリスト】
    {", ".join([log['food_name'] for log in meal_logs])}
    
    不足している栄養素があれば指摘し、逆に摂りすぎているものがあれば注意してください。
    """

    try:
        model = genai.GenerativeModel(model_name)
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        error_msg = str(e)
        print(f"[AI Advice Error] {error_msg}")
        
        # 【修正】例外をraiseせず、エラーメッセージを文字列として返す。
        # これによりst.cache_dataが結果（エラー文）をキャッシュできるため、
        # 画面更新のたびにAPIを叩きに行く無限ループを防げる。
        return f"⚠️ 現在AIアドバイスを取得できません（API制限等の理由）。時間をおいてお試しください。\n\n詳細: {error_msg}"


# --- DB操作: profiles ---

def get_user_profile(supabase, user_id):
    """ユーザー設定を取得"""
    try:
        data = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if data.data:
            return data.data[0]
        return {}
    except:
        return {}


def update_user_profile(supabase, user_id, updates):
    """ユーザー設定を更新"""
    supabase.table("profiles").update(updates).eq("id", user_id).execute()


# --- DB操作: meal_logs ---

def save_meal_log(supabase, user_id, meal_date, meal_type, text, p, f, c, cal):
    """食事ログをDBに保存"""
    supabase.table("meal_logs").insert({
        "user_id": user_id,
        "meal_date": meal_date.isoformat(),
        "meal_type": meal_type,
        "food_name": text,
        "p_val": p, "f_val": f, "c_val": c, "calories": cal
    }).execute()


def get_meal_logs(supabase, user_id, date_str):
    """指定日の食事ログを取得"""
    try:
        res = supabase.table("meal_logs").select("*") \
            .eq("user_id", user_id) \
            .eq("meal_date", date_str) \
            .order("created_at", desc=True) \
            .execute()
        return res.data
    except Exception as e:
        print(f"Log fetch error: {e}")
        return []


def delete_meal_log(supabase, log_id):
    """ログ削除"""
    supabase.table("meal_logs").delete().eq("id", log_id).execute()
