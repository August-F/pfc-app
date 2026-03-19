# リポジトリ構成の設計メモ

作成日: 2026-03-19

---

## 現在の構成

```
pfc-app/
├── .github/workflows/test.yml  ← CI（GitHub Actions）
├── docs/                       ← 設計ドキュメント（本ファイル等）
├── src/                        ← アプリ本体
│   ├── app.py
│   ├── pages/
│   ├── tests/
│   └── ...
├── CLAUDE.md
└── .gitignore
```

---

## 構成変更の経緯（2026-03-19）

### 変更前

```
pfc-app/
├── app-code/
│   └── pfc-app/        ← git リポジトリルート（旧）
│       ├── .github/
│       ├── app.py
│       └── ...
└── memo_GitHubに上げない/
```

### 変更内容と理由

| 変更 | 理由 |
|------|------|
| gitルートを `app-code/pfc-app/` → `pfc-app/` ルートへ移動 | CLAUDE.md や docs/ など、アプリ外のファイルもgit管理対象にするため |
| `app-code/pfc-app/` → `src/` にリネーム | `app-code/pfc-app/` という二重ネストが冗長だったため |
| `.github/` をルートへ移動 | GitHub Actions はリポジトリルートの `.github/` しか参照しないため（旧位置では CI が動いていなかった） |
| `memo_GitHubに上げない/` を廃止 | フォルダを削除・整理済み |
| `設計メモ/` → `docs/` にリネーム | 標準的な慣習に合わせ、gitignore対象から外してGit管理下に置くため |

### test.yml への影響

`src/` 移動に伴い、CI の作業ディレクトリを明示的に指定：

```yaml
- name: Install dependencies
  run: pip install -r requirements-dev.txt
  working-directory: src

- name: Run tests
  run: pytest --tb=short -v
  working-directory: src
```

---

## キャッシュ設計方針

（詳細は `performance_policy.md` 参照）

| キャッシュ対象 | TTL | 無効化タイミング |
|---|---|---|
| Gemini モデル一覧 | 3600秒 | TTL自然失効 |
| ユーザープロフィール | 300秒 | `update_user_profile()` 実行時に `.clear()` |
| ダッシュボード食事ログ | 60秒 | TTL自然失効 |
| Supabase クライアント | 永続 | アプリ再起動時 |

---

## 認証の現状

- 現在は認証を無効化し、固定の DEFAULT_USER_ID でシングルユーザー動作
- `auth.py` に認証フローは実装済み（将来のマルチユーザー対応時に有効化可能）
- RLS は全テーブルで有効。サーバーサイドの Streamlit から service_role key でアクセス
- 詳細は `security_policy.md` 参照
