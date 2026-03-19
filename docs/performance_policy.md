# パフォーマンス改善メモ

作成日: 2026-02-19

---

## 実施した改善

### 1. Gemini モデル一覧取得のキャッシュ化

**対象:** `services.py` `get_available_gemini_models()`

**問題:** Settings ページを開くたびに `genai.list_models()` が呼ばれ、1〜3秒のAPI遅延が発生していた。

**対策:**
```python
@st.cache_data(ttl=3600)
def get_available_gemini_models():
    ...
```
モデル一覧は頻繁に変わらないため、1時間キャッシュ。

---

### 2. プロフィール取得のキャッシュ化

**対象:** `services.py` `get_user_profile()`

**問題:** 3ページそれぞれでページロードのたびに Supabase に同一クエリを送っていた。

**対策:**
- `supabase` 引数を削除し、関数内で `get_supabase()` を呼ぶ（`@st.cache_data` 対応のため）
- `@st.cache_data(ttl=300)` を追加（5分キャッシュ）
- プロフィール更新時（`update_user_profile()`）に `get_user_profile.clear()` でキャッシュを無効化

```python
@st.cache_data(ttl=300)
def get_user_profile(user_id):
    supabase = get_supabase()
    ...

def update_user_profile(supabase, user_id, updates):
    supabase.table("profiles").update(updates)...execute()
    get_user_profile.clear()  # キャッシュ無効化
```

---

### 3. 食事ログの重複取得を削除

**対象:** `pages/meal_record.py`

**問題:** フォーム送信時に `get_meal_logs()` を2回呼んでいた（117行目と旧127行目）。

**対策:** 2回目の呼び出しを削除し、117行目で取得済みの `logs` を再利用。

---

### 4. `init_gemini()` の重複呼び出しを削除

**対象:** `pages/settings.py`

**問題:** `app.py` で呼んでいるにもかかわらず `settings.py` でも呼んでいた。

**対策:** `settings.py` の `init_gemini()` 呼び出しと import を削除。

---

### 5. 食事登録時の Gemini 呼び出しを軽量化

**対象:** `pages/meal_record.py`

**問題:** 「AI解析して記録」ボタン押下時に PFC 解析＋アドバイス生成を1回の API 呼び出しで行っていた。プロンプトが 1,800文字以上あり 5〜8秒かかっていた。

**対策:**
- `analyze_meal_with_advice()` → `analyze_meal_with_gemini()` に変更
- `analyze_meal_with_gemini` は PFC のみを推測する 210文字の軽量プロンプト（2〜3秒）
- アドバイスはリラン後に既存の spinner ロジックで自動生成（`advice_needs_refresh = True`）
- `st.success() + time.sleep(1)` → `st.toast()` に変更（1秒削減）

```python
# Before（遅い）
result = analyze_meal_with_advice(food_text, model, profile_d, logged_meals, totals, targets, meal_type)
p, f, c, cal, advice = result
st.success(...); time.sleep(1); st.rerun()

# After（速い）
result = analyze_meal_with_gemini(food_text, model)
p, f, c, cal = result
st.session_state["advice_needs_refresh"] = True
st.toast(...); st.rerun()
```

---

## 効果まとめ

| 対策 | 削減時間 |
|------|---------|
| Gemini モデル一覧キャッシュ | 1〜3秒（Settings ページ2回目以降） |
| プロフィールキャッシュ | 0.5〜1秒（全ページ2回目以降） |
| 重複ログ取得削除 | 0.5〜1秒（フォーム送信時） |
| 食事登録プロンプト軽量化 | 3〜5秒（毎回の登録） |
| toast 置き換え | 1秒（毎回の登録） |

---

## キャッシュ設計方針

| キャッシュ対象 | TTL | 無効化タイミング |
|--------------|-----|----------------|
| Gemini モデル一覧 | 3600秒（1時間） | なし（TTL自然失効） |
| ユーザープロフィール | 300秒（5分） | `update_user_profile()` 実行時に `.clear()` |
| ダッシュボード食事ログ | 60秒 | TTL自然失効 |
| Supabase クライアント | 永続（`@st.cache_resource`） | アプリ再起動時 |

## 今後の注意事項

- `@st.cache_data` はデフォルトで引数をハッシュキーとして使用するため、**Supabase クライアントのような非シリアライザブルなオブジェクトは引数に渡さない**こと。代わりに関数内で `get_supabase()` を呼ぶ（`dashboard.py` の `fetch_meal_logs_range` パターンを参考）。
- キャッシュを使う関数でデータを書き込んだ場合は、対応するキャッシュを `.clear()` で無効化すること。
- `analyze_meal_with_advice()` は現在 `meal_record.py` から使われていないが、関数自体は `services.py` に残してある。将来的に不要であれば削除可。
