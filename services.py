import streamlit as st
import google.generativeai as genai
import json


# --- Gemini関連 ---

def get_available_gemini_models():
    """Gemini APIから利用可能なテキスト生成モデル一覧を取得"""
    try:
        models = []
        for m in genai.list_models():
            model_name = m.name.replace("models/", "")
            
            # テキスト生成をサポートしているか確認
            if 'generateContent' not in m.supported_generation_methods:
                continue
            
            # テキスト出力モデルのみをフィルタリング
            # - "gemini-" で始まるモデルのみ（画像生成モデル等を除外）
            # - 埋め込みモデル（embedding）を除外
            # - 画像生成モデル（imagen）を除外
            # - AQAモデルを除外
            if not model_name.startswith("gemini-"):
                continue
            if "embedding" in model_name.lower():
                continue
            if "imagen" in model_name.lower():
                continue
            if "aqa" in model_name.lower():
                continue
            
            models.append(model_name)
        
        if models:
            return models
    except Exception as e:
        print(f"モデル一覧取得エラー: {e}")
    return ["gemini-3-flash", "gemini-2.5-flash", "gemini-3-pro"]


def analyze_meal_with_gemini(text, model_name="gemini-3-flash"):
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
        # 画面上にデバッグ用のエラー内容を表示
        st.error(f"Error: {type(e).__name__} - {str(e)}")
        
        return None        

def generate_pfc_summary(totals, targets):
    """PFCサマリー行を生成（AIを使わない）"""
    rem_cal = targets["cal"] - totals["cal"]
    rem_p = targets["p"] - totals["p"]
    rem_f = targets["f"] - totals["f"]
    rem_c = targets["c"] - totals["c"]

    # +/-表記の準備（+は超過、-は不足）
    def fmt(val):
        if val <= 0:
            return f"+{abs(int(val))}"
        else:
            return f"-{int(val)}"

    fmt_p = fmt(rem_p)
    fmt_f = fmt(rem_f)
    fmt_c = fmt(rem_c)

    if rem_cal > 0:
        return f"🔥 あと{int(rem_cal)}kcal！（P: {fmt_p}g / F: {fmt_f}g / C: {fmt_c}g）"
    else:
        return f"🔥 {abs(int(rem_cal))}kcalオーバー！（P: {fmt_p}g / F: {fmt_f}g / C: {fmt_c}g）"


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

    # 記録済みの食事内容をテキスト化
    if logged_meals:
        meals_detail = "\n".join(
            f"・{m['meal_type']}: {m['food_name']}（{m['calories']}kcal / P:{m['p_val']}g F:{m['f_val']}g C:{m['c_val']}g）"
            for m in logged_meals
        )
    else:
        meals_detail = "まだ記録なし"

    # +/-表記の準備（+は超過、-は不足）
    def fmt(val):
        if val <= 0:
            return f"+{abs(int(val))}"
        else:
            return f"-{int(val)}"
    fmt_p = fmt(rem_p)
    fmt_f = fmt(rem_f)
    fmt_c = fmt(rem_c)

    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""あなたはマッチョなパーソナルトレーナーのキャラクターです。
以下のルールを必ず守ってください:
- 必ず💪🏋️‍♀️🔥などの絵文字を毎回複数使う
- 必ずですます調で話す
- 明るくポジティブに励ます

以下の情報をもとに、食事アドバイスをしてください。

■ 本日の記録
{meals_detail}

■ 目標との差（+は超過、-は不足）
カロリー: {fmt(rem_cal)} kcal / P: {fmt_p}g / F: {fmt_f}g / C: {fmt_c}g

■ 食事状況
{remaining_str}

■ ユーザーの好み
好きな食べ物: {likes}
苦手な食べ物: {dislikes}
その他要望: {prefs}

■ 出力ルール
- 超過している項目がある場合: 記録済みの食事内容に触れながら「○○は△△が豊富ですが□□も高めなので…」のように原因を具体的に説明し、「明日は○○など、□□ひかえめな食材で調整しましょう💪」と提案する
- 不足している場合: 未記録の食事タイミングごとに具体的なメニューを1〜2品提案する
- 全て記録済みで超過なしの場合: 全体の振り返りを一言で褒める
- 提案は好きな食べ物に限定せず、PFCバランスに合う一般的なメニューを幅広く提案してよい
- ただし苦手な食べ物は必ず避けること
- 全体で80文字〜150文字程度に収める
- マークダウン記法は使わない（絵文字はOK。💪🏋️‍♀️🔥を積極的に使う）
- カロリーやPFCの数値は別途表示されるため、アドバイスには含めない
"""
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        error_msg = str(e)
        print(f"[AI Advice Error] {error_msg}")
        # 429エラー（レート制限）の場合は、そのままraiseして呼び出し元で処理
        # キャッシュされないようにするため、例外をそのまま投げる
        raise


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
