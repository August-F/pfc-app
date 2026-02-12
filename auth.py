import streamlit as st
import time

def login_signup(supabase):
    """ログイン・サインアップ画面を描画し、認証処理を行う"""
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
                st.success("ログイン成功！")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                # エラーの詳細を表示せず、一般的なメッセージにする（セキュリティ向上）
                st.error("ログイン失敗: メールアドレスかパスワードが間違っています。")

    with tab2:
        st.caption("登録後、[ログイン] タブからログインしてください")
        
        new_email = st.text_input("メールアドレス", key="signup_email")
        new_password = st.text_input("パスワード", type="password", key="signup_pass")
        
        if st.button("アカウント作成"):
            try:
                response = supabase.auth.sign_up({
                    "email": new_email, 
                    "password": new_password
                })
                st.success("登録完了！ [ログイン] タブに切り替えてログインしてください。")
                    
            except Exception as e:
                st.error(f"登録エラー: {e}")
