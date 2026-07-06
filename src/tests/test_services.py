"""
services.py のユニットテスト

外部API (Gemini / Supabase) はモックで差し替えてテストする。
"""
import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# generate_pfc_summary のテスト（純粋関数 — モック不要）
# ---------------------------------------------------------------------------

from services import generate_pfc_summary


class TestGeneratePfcSummary:
    """generate_pfc_summary: PFCサマリー文字列の生成ロジックを検証"""

    def test_under_target_shows_remaining_calories(self):
        """目標カロリー未達の場合: 'あとXkcal' が含まれること"""
        totals  = {"cal": 1500, "p": 80, "f": 40, "c": 200}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "あと500kcal" in result

    def test_over_target_shows_over_calories(self):
        """目標カロリー超過の場合: 'XkcalオーバーI' が含まれること"""
        totals  = {"cal": 2500, "p": 120, "f": 70, "c": 300}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "500kcalオーバー" in result

    def test_under_target_pfc_shows_minus(self):
        """PFCが不足している場合: '-Xg' 形式で表示されること"""
        totals  = {"cal": 1500, "p": 80, "f": 40, "c": 200}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "P: -20g" in result
        assert "F: -20g" in result
        assert "C: -50g" in result

    def test_over_target_pfc_shows_plus(self):
        """PFCが超過している場合: '+Xg' 形式で表示されること"""
        totals  = {"cal": 2500, "p": 120, "f": 70, "c": 300}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "P: +20g" in result
        assert "F: +10g" in result
        assert "C: +50g" in result

    def test_zero_totals(self):
        """記録がゼロの状態: 目標値がそのまま不足量として表示されること"""
        totals  = {"cal": 0, "p": 0, "f": 0, "c": 0}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "あと2000kcal" in result
        assert "P: -100g" in result

    def test_exactly_at_target(self):
        """ちょうど目標値のとき: rem_cal==0 なので 'オーバー' 側になること"""
        totals  = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "0kcalオーバー" in result

    def test_returns_string(self):
        """戻り値が文字列であること"""
        totals  = {"cal": 1000, "p": 50, "f": 30, "c": 100}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert isinstance(result, str)

    def test_always_contains_fire_emoji(self):
        """返り値に 🔥 絵文字が含まれること"""
        totals  = {"cal": 1000, "p": 50, "f": 30, "c": 100}
        targets = {"cal": 2000, "p": 100, "f": 60, "c": 250}
        result = generate_pfc_summary(totals, targets)
        assert "🔥" in result


# ---------------------------------------------------------------------------
# analyze_meal_with_gemini のテスト（Gemini API をモック）
# ---------------------------------------------------------------------------

from services import analyze_meal_with_gemini


class TestAnalyzeMealWithGemini:
    """analyze_meal_with_gemini: Gemini APIの呼び出しとJSONパースを検証"""

    def test_short_text_returns_none(self):
        """1文字以下の入力は None を返すこと（API呼び出し不要）"""
        result = analyze_meal_with_gemini("a")
        assert result is None

    def test_empty_text_returns_none(self):
        """空文字は None を返すこと"""
        result = analyze_meal_with_gemini("")
        assert result is None

    def test_valid_response_parsed_correctly(self, mocker):
        """正常なJSONレスポンスが正しくパースされること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": 500, "p": 30, "f": 15, "c": 60, "iron_mg": 2.5, "folate_ug": 80.0, "calcium_mg": 150.0, "vitamin_d_ug": 3.0}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("鶏むね肉とご飯", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert p == 30
        assert f == 15
        assert c == 60
        assert cal == 500
        assert iron == 2.5
        assert folate == 80.0
        assert calcium == 150.0
        assert vit_d == 3.0

    def test_markdown_fences_are_stripped(self, mocker):
        """コードブロック(```json ... ```)付きのレスポンスも正しくパースされること"""
        mock_response = MagicMock()
        mock_response.text = '```json\n{"cal": 400, "p": 25, "f": 10, "c": 50, "iron_mg": 1.0, "folate_ug": 40.0, "calcium_mg": 100.0, "vitamin_d_ug": 1.0}\n```'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("サラダチキン", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert cal == 400

    def test_invalid_json_returns_none(self, mocker):
        """不正なJSONが返ってきたとき None を返すこと"""
        mock_response = MagicMock()
        mock_response.text = "これはJSONではありません"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)
        mocker.patch("streamlit.error")  # st.error の呼び出しを無効化

        result = analyze_meal_with_gemini("テスト食品", "gemini-flash")

        assert result is None

    def test_missing_keys_default_to_zero(self, mocker):
        """JSONキーが一部欠けていても 0 として扱われること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": 300}'  # p, f, c, 微量栄養素 が欠落
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("テスト食品", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert p == 0
        assert f == 0
        assert c == 0
        assert cal == 300
        assert iron == 0
        assert folate == 0
        assert calcium == 0
        assert vit_d == 0

    def test_string_values_are_coerced_to_numbers(self, mocker):
        """数値が文字列で返ってきても数値に変換されること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": "500", "p": "30", "f": "15", "c": "60", "iron_mg": "2.5", "folate_ug": "80", "calcium_mg": "150", "vitamin_d_ug": "3"}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("鶏むね肉とご飯", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert p == 30
        assert cal == 500
        assert iron == 2.5

    def test_negative_values_are_clamped_to_zero(self, mocker):
        """負値が返ってきても 0 にクランプされること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": 300, "p": -5, "f": 10, "c": -20, "iron_mg": -1.0, "folate_ug": 40.0, "calcium_mg": 100.0, "vitamin_d_ug": 1.0}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("テスト食品", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert p == 0
        assert c == 0
        assert iron == 0
        assert cal == 300

    def test_non_numeric_values_default_to_zero(self, mocker):
        """数値に変換できない値は 0 として扱われること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": "不明", "p": null, "f": 10, "c": 60, "iron_mg": 1.0, "folate_ug": 40.0, "calcium_mg": 100.0, "vitamin_d_ug": 1.0}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        result = analyze_meal_with_gemini("テスト食品", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert cal == 0
        assert p == 0
        assert f == 10


# ---------------------------------------------------------------------------
# get_available_gemini_models のテスト（Gemini API をモック）
# ---------------------------------------------------------------------------

from types import SimpleNamespace
from services import get_available_gemini_models


def _mock_model(name, actions=("generateContent",)):
    """genai のモデルオブジェクトを模倣する"""
    return SimpleNamespace(name=name, supported_actions=list(actions))


class TestGetAvailableGeminiModels:
    """get_available_gemini_models: モデルのフィルタリングロジックを検証"""

    def setup_method(self):
        # @st.cache_data のキャッシュをテスト間でクリアする
        get_available_gemini_models.clear()

    def test_filters_non_text_models(self, mocker):
        """embedding / imagen / aqa / generateContent非対応モデルが除外されること"""
        mock_client = MagicMock()
        mock_client.models.list.return_value = [
            _mock_model("models/gemini-2.5-flash"),
            _mock_model("models/gemini-embedding-001"),
            _mock_model("models/imagen-3.0-generate"),
            _mock_model("models/aqa"),
            _mock_model("models/gemini-2.5-pro", actions=["countTokens"]),  # generateContent 非対応
            _mock_model("models/text-bison"),  # gemini- で始まらない
        ]
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        models = get_available_gemini_models()

        assert models == ["gemini-2.5-flash"]

    def test_fallback_contains_default_model(self, mocker):
        """API障害時のフォールバック一覧に selected_model の初期値が含まれること"""
        mocker.patch("services.get_gemini_client", side_effect=Exception("API down"))

        models = get_available_gemini_models()

        assert "gemini-flash-latest" in models

    def test_empty_list_returns_fallback(self, mocker):
        """モデル一覧が空のときフォールバック一覧が返ること"""
        mock_client = MagicMock()
        mock_client.models.list.return_value = []
        mocker.patch("services.get_gemini_client", return_value=mock_client)

        models = get_available_gemini_models()

        assert "gemini-flash-latest" in models


# ---------------------------------------------------------------------------
# save_meal_log のテスト（Supabase をモック）
# ---------------------------------------------------------------------------

from datetime import date
from services import save_meal_log


class TestSaveMealLog:
    """save_meal_log: 丸め処理と行データの構築を検証"""

    def _insert_arg(self, supabase):
        return supabase.table.return_value.insert.call_args[0][0]

    def test_pfc_values_are_rounded_to_int(self):
        """PFC・カロリーが整数に丸められること"""
        supabase = MagicMock()
        save_meal_log(supabase, "uid", date(2026, 7, 7), "朝食", "テスト",
                      10.6, 5.4, 20.2, 300.7)
        row = self._insert_arg(supabase)
        assert row["p_val"] == 11
        assert row["f_val"] == 5
        assert row["c_val"] == 20
        assert row["calories"] == 301

    def test_micronutrients_rounded_to_one_decimal(self):
        """微量栄養素が小数第1位に丸められること"""
        supabase = MagicMock()
        save_meal_log(supabase, "uid", date(2026, 7, 7), "朝食", "テスト",
                      10, 5, 20, 300,
                      iron_mg=2.34, folate_ug=80.16, calcium_mg=150.04, vitamin_d_ug=3.28)
        row = self._insert_arg(supabase)
        assert row["iron_mg"] == 2.3
        assert row["folate_ug"] == 80.2
        assert row["calcium_mg"] == 150.0
        assert row["vitamin_d_ug"] == 3.3

    def test_micronutrients_omitted_when_none(self):
        """微量栄養素が None のとき行データに含まれないこと（テンプレート登録時）"""
        supabase = MagicMock()
        save_meal_log(supabase, "uid", date(2026, 7, 7), "昼食", "テスト", 10, 5, 20, 300)
        row = self._insert_arg(supabase)
        assert "iron_mg" not in row
        assert "folate_ug" not in row
        assert "calcium_mg" not in row
        assert "vitamin_d_ug" not in row

    def test_meal_date_is_isoformat(self):
        """meal_date が ISO 形式の文字列で保存されること"""
        supabase = MagicMock()
        save_meal_log(supabase, "uid", date(2026, 7, 7), "夕食", "テスト", 10, 5, 20, 300)
        row = self._insert_arg(supabase)
        assert row["meal_date"] == "2026-07-07"


# ---------------------------------------------------------------------------
# aggregate_daily のテスト（純粋関数 — モック不要）
# ---------------------------------------------------------------------------

from services import aggregate_daily


class TestAggregateDaily:
    """aggregate_daily: 日次集計ロジックを検証"""

    START = date(2026, 7, 1)

    def test_returns_row_per_day(self):
        """日数分の行が生成されること（記録なしの日も含む）"""
        df = aggregate_daily([], self.START, 7)
        assert len(df) == 7
        assert df.iloc[0]["date"] == "2026-07-01"
        assert df.iloc[6]["date"] == "2026-07-07"

    def test_basic_aggregation(self):
        """1件のログが正しく集計されること（p_cal/f_cal/c_cal のカロリー換算含む）"""
        logs = [{"meal_date": "2026-07-01", "calories": 500, "p_val": 30, "f_val": 10, "c_val": 60}]
        df = aggregate_daily(logs, self.START, 7)
        row = df.iloc[0]
        assert row["calorie"] == 500
        assert row["protein"] == 30
        assert row["p_cal"] == 120   # 30g × 4kcal
        assert row["f_cal"] == 90    # 10g × 9kcal
        assert row["c_cal"] == 240   # 60g × 4kcal
        assert row["meal_count"] == 1

    def test_multiple_logs_same_day_are_summed(self):
        """同日の複数ログが合算されること"""
        logs = [
            {"meal_date": "2026-07-02", "calories": 400, "p_val": 20, "f_val": 10, "c_val": 50},
            {"meal_date": "2026-07-02", "calories": 600, "p_val": 30, "f_val": 15, "c_val": 70},
        ]
        df = aggregate_daily(logs, self.START, 7)
        row = df.iloc[1]
        assert row["calorie"] == 1000
        assert row["protein"] == 50
        assert row["meal_count"] == 2

    def test_out_of_range_logs_are_ignored(self):
        """期間外の日付のログが無視されること"""
        logs = [{"meal_date": "2026-06-30", "calories": 500, "p_val": 30, "f_val": 10, "c_val": 60}]
        df = aggregate_daily(logs, self.START, 7)
        assert df["calorie"].sum() == 0
        assert df["meal_count"].sum() == 0

    def test_none_values_are_treated_as_zero(self):
        """ログの値が None でも 0 として集計されること（Supabase null 値の模倣）"""
        logs = [{"meal_date": "2026-07-01", "calories": None, "p_val": None, "f_val": 5, "c_val": None}]
        df = aggregate_daily(logs, self.START, 7)
        row = df.iloc[0]
        assert row["calorie"] == 0
        assert row["fat"] == 5
        assert row["f_cal"] == 45
        assert row["meal_count"] == 1

    def test_no_meal_days_have_zero_count(self):
        """記録のない日は meal_count=0 であること（移動平均の対象外判定に使用）"""
        logs = [{"meal_date": "2026-07-03", "calories": 500, "p_val": 30, "f_val": 10, "c_val": 60}]
        df = aggregate_daily(logs, self.START, 7)
        assert int((df["meal_count"] > 0).sum()) == 1
