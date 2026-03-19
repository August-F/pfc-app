# セキュリティ設定メモ

作成日: 2026-02-19

---

## 実施した修正内容

### 1. RLS（Row Level Security）の有効化

Supabase の Security Advisor で「RLS ポリシーが存在するがテーブルで RLS が無効」と指摘されたため対応。

**対象テーブル・実行 SQL：**

```sql
ALTER TABLE public.meal_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
```

各テーブルには以下のポリシーが設定済み：

- `meal_logs`：Users can view/insert/update/delete own logs（`auth.uid() = user_id`）
- `profiles`：Users can view/insert/update own profile（`auth.uid() = id`）

---

### 2. handle_new_user 関数の search_path 固定

Supabase の Security Advisor で「`SECURITY DEFINER` 関数の search_path が固定されていない」と指摘されたため対応。

**修正後の関数定義：**

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''         -- ← 追加
AS $function$
BEGIN
  INSERT INTO public.profiles (id)
  VALUES (new.id);
  RETURN new;
END;
$function$;
```

`SET search_path = ''` により search_path injection 攻撃を防止。
テーブル参照はすべて `public.profiles` と完全修飾済みのため動作に影響なし。

---

### 3. 流出パスワードチェック（対応不要）

HaveIBeenPwned.org 連携によるパスワードチェック機能は **Pro プラン以上でのみ利用可能**。
現在のプランでは有効化できないため対応不要。

---

## RLS 有効化に伴うアプリ対応

### 問題

アプリは認証を無効化したデフォルトユーザー（固定 UUID）で動作しているため、RLS 有効化後に Supabase クライアントに JWT が設定されず `auth.uid()` が null となり、INSERT / SELECT がすべて RLS に阻まれエラーになった。

### 方針：service_role key の使用

Streamlit はサーバーサイドで動作するため、service_role key をサーバー側で使用することは安全。

- service_role key は **Streamlit Cloud の Secrets にのみ保存**し、コードや GitHub には含めない
- anon key は fallback として残す

**Streamlit Secrets 設定（`secrets.toml` 相当）：**

```toml
[supabase]
url = "https://xxxx.supabase.co"
key = "eyJ..."           # anon key（fallback）
service_key = "eyJ..."   # service_role key（実際に使用）
```

**`config.py` の変更内容：**

```python
# service_key が設定されていればサーバーサイド用として使用（RLS をバイパス）
key = st.secrets["supabase"].get("service_key") or st.secrets["supabase"]["key"]
```

### なぜ service_role key で安全か

| 観点 | 状況 |
|------|------|
| ブラウザへの露出 | なし（Streamlit はサーバーサイド実行） |
| Git への露出 | なし（Streamlit Cloud Secrets にのみ保存） |
| RLS の意義 | 外部からの直接 API アクセスは引き続き RLS で保護される |
| アプリの性質 | 個人用シングルユーザーアプリ |

---

## 今後の注意事項

- service_role key が漏洩した場合は Supabase Dashboard → Settings → API から即座に再生成すること
- 将来マルチユーザー対応する場合は、認証フロー（`auth.py` に実装済み）を有効化し service_role key 不要の構成に移行すること
