# 🍽️ AI PFC Manager

食事内容をテキストで入力するだけで、AIが自動でPFC（タンパク質・脂質・炭水化物）とカロリーを解析・記録してくれるWebアプリです。


## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| フロントエンド / フレームワーク | [Streamlit](https://streamlit.io/) |
| データベース / 認証 | [Supabase](https://supabase.com/)（フリープラン） |
| AI解析 | [Google Gemini API](https://ai.google.dev/) |
| グラフ描画 | Plotly |


## 機能

- **AI食事解析** — テキストで食事内容を入力すると、Gemini APIがカロリー・PFC・微量栄養素（鉄・葉酸・カルシウム・ビタミンD）を自動推定
- **📊 PFCダッシュボード** — 日次のカロリー・PFC推移をグラフで可視化（7/14/30日間切り替え対応）
- **目標管理** — カロリー・P・F・Cの目標値を設定し、達成率をトラッキング
- **テンプレート機能** — よく食べる食事をテンプレート登録して素早く記録
- **栄養成分リファレンス** — カテゴリ別の食品栄養成分表を参照
- **AIモデル選択** — 使用するGeminiモデルを設定画面から選択可能
- **LINE / クリップボード共有** — 1日の食事記録をワンタップで共有


## ファイル構成

```
pfc-app/
├── .github/
│   └── workflows/
│       └── test.yml        # CI（GitHub Actions）
├── src/
│   ├── app.py              # エントリーポイント（共通設定 + st.navigation）
│   ├── pages/
│   │   ├── meal_record.py  # 🍽️ 食事記録ページ（メイン）
│   │   ├── dashboard.py    # 📊 PFCダッシュボード（日次推移グラフ）
│   │   ├── nutrition.py    # 🥗 栄養成分リファレンス
│   │   └── settings.py     # ⚙️ 設定（目標・モデル・テンプレート管理）
│   ├── auth.py             # ログイン・新規登録画面
│   ├── config.py           # Supabase・Gemini APIの初期化
│   ├── services.py         # DB操作（profile / meal_logs / templates）+ Gemini解析
│   ├── charts.py           # 達成率グラフの描画
│   ├── bg.png              # 背景画像
│   ├── tests/
│   │   ├── conftest.py     # pytest共通設定
│   │   ├── test_services.py # services.pyのユニットテスト
│   │   └── test_charts.py  # charts.pyのユニットテスト
│   ├── hooks/
│   │   └── pre-commit      # Git pre-commitフック
│   ├── pytest.ini          # pytest設定
│   ├── requirements.txt    # 本番依存パッケージ
│   └── requirements-dev.txt # 開発依存パッケージ（pytest等）
└── 設計メモ/               # 設計ドキュメント（gitignore対象）
```

> ページルーティングには [Streamlit推奨の `st.navigation`](https://docs.streamlit.io/develop/concepts/multipage-apps/overview) を使用しています。


## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r src/requirements.txt
```

開発・テスト環境の場合は追加でインストール：

```bash
pip install -r src/requirements-dev.txt
```

### 2. Streamlit Secrets の設定

`src/.streamlit/secrets.toml` を作成し、以下を記入してください。

```toml
[supabase]
url = "https://xxxxx.supabase.co"
key = "your-anon-key"           # anon key（fallback）
service_key = "your-service-role-key"  # service_role key（実際に使用）

[gemini]
api_key = "your-gemini-api-key"
```

> **service_role key について：** 全テーブルでRLS（Row Level Security）が有効なため、サーバーサイドで動作するStreamlitアプリはservice_role keyを使用してRLSをバイパスします。このキーはStreamlit CloudのSecretsにのみ保存し、コードやGitHubには含めないでください。

### 3. アプリの起動

```bash
streamlit run src/app.py
```

### 4. テストの実行

```bash
cd src && pytest tests/
```


## データベース構成（Supabase）

### meal_logs

| カラム | 型 | 説明 |
|-------|----|------|
| id | uuid | 主キー |
| user_id | uuid | auth.users.id への外部キー |
| meal_date | date | 食事日 |
| meal_type | text | 朝食 / 昼食 / 夕食 / 間食 |
| food_name | text | 食事内容テキスト |
| calories | int4 | カロリー (kcal) |
| p_val | int4 | タンパク質 (g) |
| f_val | int4 | 脂質 (g) |
| c_val | int4 | 炭水化物 (g) |
| iron_mg | float8 | 鉄 (mg) |
| folate_ug | float8 | 葉酸 (μg) |
| calcium_mg | float8 | カルシウム (mg) |
| vitamin_d_ug | float8 | ビタミンD (μg) |
| created_at | timestamptz | 作成日時 |

### profiles

| カラム | 型 | 説明 |
|-------|----|------|
| id | uuid | 主キー（auth.users.id） |
| declaration | text | 目標宣言 |
| target_calories | int4 | 目標カロリー |
| target_p | int4 | 目標タンパク質 (g) |
| target_f | int4 | 目標脂質 (g) |
| target_c | int4 | 目標炭水化物 (g) |
| likes | text | 好きな食べ物 |
| dislikes | text | 苦手な食べ物 |
| preferences | text | その他要望 |
| updated_at | timestamptz | 更新日時 |

### meal_templates

| カラム | 型 | 説明 |
|-------|----|------|
| id | uuid | 主キー |
| user_id | uuid | auth.users.id への外部キー |
| name | text | テンプレート名 |
| food_name | text | 食品名 |
| calories | numeric | カロリー (kcal) |
| p_val | numeric | タンパク質 (g) |
| f_val | numeric | 脂質 (g) |
| c_val | numeric | 炭水化物 (g) |
| meal_type | text | デフォルト食事タイプ |
| created_at | timestamptz | 作成日時 |
