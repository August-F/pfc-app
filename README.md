# 🍽️ AI PFC Manager

食事内容をテキストで入力するだけで、AIが自動でPFC（タンパク質・脂質・炭水化物）とカロリーを解析・記録してくれるWebアプリです。


## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| フロントエンド / フレームワーク | [Streamlit](https://streamlit.io/) |
| データベース / 認証 | [Supabase](https://supabase.com/)（フリープラン） |
| AI解析 | [Google Gemini API](https://ai.google.dev/) |
| グラフ描画 | matplotlib |

## ファイル構成

```
pfc-app/
├── app.py              # エントリーポイント + メインUI
├── auth.py             # ログイン・新規登録画面
├── config.py           # Supabase・Gemini APIの初期化
├── services.py         # DB操作（profile / meal_logs）+ Gemini解析
├── charts.py           # 達成率グラフの描画
└── requirements.txt    # Pythonパッケージ一覧
```

