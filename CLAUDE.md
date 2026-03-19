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
└── 設計メモ/               ← 設計ドキュメント（gitignore対象）
```

## 主な機能

- AI食事解析（テキスト入力 → Gemini API → PFC自動推定）
- AIアドバイス生成
- PFCダッシュボード（7/14/30日間グラフ）
- 目標管理・達成率トラッキング
- LINE / クリップボード共有

## 開発ルール

- 環境変数は `.env` で管理（絶対にコミットしない）
- テストは `tests/` に追加する
- Supabase接続情報は `config.py` 経由で取得する

## Claudeへの指示

- コードを変更する前に必ず該当ファイルを読むこと
- `設計メモ/` フォルダは読み込み・編集しないこと
- `.env` ファイルは絶対に読まない・編集しない
- Gemini APIのプロンプトを変更する際は既存の出力フォーマットとの互換性を確認すること
