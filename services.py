import streamlit as st
import google.generativeai as genai
import json


# --- Gemini関連 ---

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
        return supabase.table("meal_logs").select("*").eq("user_id", user_id).eq("meal_date", date_str).execute()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None


def delete_meal_log(supabase, log_id):
    """食事ログを削除"""
    supabase.table("meal_logs").delete().eq("id", log_id).execute()
