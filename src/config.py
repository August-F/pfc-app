import streamlit as st
from supabase import create_client, Client
from google import genai

# --- Supabase接続 ---
@st.cache_resource
def init_supabase():
    """Supabaseクライアントを初期化して返す"""
    if "supabase" in st.secrets:
        url = st.secrets["supabase"]["url"]
        # service_key が設定されていればサーバーサイド用として使用（RLS をバイパス）
        key = st.secrets["supabase"].get("service_key") or st.secrets["supabase"]["key"]
        return create_client(url, key)
    return None

def get_supabase() -> Client:
    """Supabaseクライアントを取得（エラー時はst.stop()）"""
    try:
        client = init_supabase()
        if client is None:
            st.error("Supabaseの接続情報が設定されていません。secrets.tomlを確認してください。")
            st.stop()
        return client
    except Exception as e:
        st.error(f"Supabase接続エラー: {e}")
        st.stop()

# --- Gemini接続 ---
@st.cache_resource
def get_gemini_client():
    """Gemini APIクライアントを初期化して返す"""
    if "gemini" in st.secrets:
        return genai.Client(api_key=st.secrets["gemini"]["api_key"])
    return None
