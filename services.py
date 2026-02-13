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


def generate_meal_advice(model_name, profile, logged_meals, totals, targets):
    """Geminiで残りの食事アドバイスを生成"""
    rem_cal = targets["cal"] - totals["cal"]
    rem_p = targets["p"] - totals["p"]
    rem_f = targets["f"] - totals["f"]
    rem_c = targets["c"] - totals["c"]

    # 記録済みのタイミングを取得
    logged_types = set(m["meal_type"] for m in logged_meals) if logged_meals else set()
    all_types = ["朝食", "昼食", "夕食", "間食"]
    remaining_types = [t for t in all_types if t not in logged_types]

    if not remaining_types:
        remaining_str = "本日の食事は全て記録済みです"
    else:
        remaining_str = "、".join(remaining_types) + " がまだ未記録です"

    likes = profile.get("likes") or "特になし"
    dislikes = profile.get("dislikes") or "特になし"
    prefs = profile.get("preferences") or "特になし"

    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""あなたはフレンドリーな栄養管理アドバイザーです。
以下の情報をもとに、残りの食事について短くアドバイスしてください。

■ 残り必要量
カロリー: {rem_cal} kcal / たんぱく質: {rem_p}g / 脂質: {rem_f}g / 炭水化物: {rem_c}g

■ 食事状況
{remaining_str}

■ ユーザーの好み
好きな食べ物: {likes}
苦手な食べ物: {dislikes}
その他要望: {prefs}

■ 出力ルール
- まず1行目に「あと○○kcal！（P: ○g / F: ○g / C: ○g）」と残量サマリーを書く（残りがマイナスの項目は「OK」と表記）
- 2行目以降に、未記録の食事タイミングごとに具体的なメニューを1〜2品ずつ提案する
- 提案は好きな食べ物に限定せず、残りのPFCバランスに合う一般的なメニューを幅広く提案してよい
- ただし苦手な食べ物は必ず避けること
- 全て記録済みの場合は、全体の振り返りコメントを一言だけ書く
- 全体で100文字〜150文字程度に収める
- マークダウン記法は使わない
"""
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return None
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
