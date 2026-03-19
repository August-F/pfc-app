# CLAUDE.md — AI PFC Manager

## プロジェクト概要

食事内容をテキスト入力するだけでAIがPFC（タンパク質・脂質・炭水化物）とカロリーを自動解析・記録するWebアプリ。

- **フレームワーク：** Streamlit
- **データベース / 認証：** Supabase（フリープラン）
- **AI解析：** Google Gemini API
- **グラフ：** Plotly

## ディレクトリ構成

```
pfc-app/
├── CLAUDE.md
├── .github/
│   └── workflows/
│       └── test.yml            ← CI（GitHub Actions）
├── src/
│   ├── app.py              ← エントリーポイント
│   ├── auth.py             ← 認証
│   ├── config.py           ← Supabase・Gemini設定
│   ├── charts.py           ← グラフ描画
│   ├── services.py         ← ビジネスロジック
│   ├── pages/              ← 各ページ
│   ├── hooks/              ← カスタムフック
│   ├── tests/              ← テスト
│   ├── requirements.txt
│   └── requirements-dev.txt
└── docs/                   ← 設計ドキュメント（security_policy.md, performance_policy.md 等）
```

## 主な機能

- AI食事解析（テキスト入力 → Gemini API → PFC・微量栄養素自動推定）
- PFCダッシュボード（7/14/30日間グラフ）
- 目標管理・達成率トラッキング
- テンプレート機能（よく食べる食事を登録して素早く記録）
- 栄養成分リファレンス（カテゴリ別食品データの参照）
- LINE / クリップボード共有
- ※ AIアドバイス生成は現在コード上で一時無効化中

## ページ構成（src/pages/）

| ファイル | 役割 |
|---|---|
| `meal_record.py` | 食事記録（メインページ） |
| `dashboard.py` | PFCダッシュボード（日次推移グラフ） |
| `nutrition.py` | 栄養成分リファレンス |
| `settings.py` | 目標・AIモデル・テンプレート管理 |

## 開発ルール

- シークレットは `src/.streamlit/secrets.toml` で管理（絶対にコミットしない）
- テストは `src/tests/` に追加する
- Supabase接続情報は `src/config.py` 経由で取得する
- コマンドはリポジトリルートから実行する（例: `streamlit run src/app.py`、`cd src && pytest tests/`）

## Claudeへの指示

- コードを変更する前に必ず該当ファイルを読むこと
- `docs/` フォルダは読み込み可。設計上の判断や背景をメモする必要があれば追記すること
- `src/.streamlit/secrets.toml` は絶対に読まない・編集しない
- Gemini APIのプロンプトを変更する際は既存の出力フォーマットとの互換性を確認すること
