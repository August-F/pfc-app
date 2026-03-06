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
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mocker.patch("services.genai.GenerativeModel", return_value=mock_model)

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
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mocker.patch("services.genai.GenerativeModel", return_value=mock_model)

        result = analyze_meal_with_gemini("サラダチキン", "gemini-flash")

        assert result is not None
        p, f, c, cal, iron, folate, calcium, vit_d = result
        assert cal == 400

    def test_invalid_json_returns_none(self, mocker):
        """不正なJSONが返ってきたとき None を返すこと"""
        mock_response = MagicMock()
        mock_response.text = "これはJSONではありません"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mocker.patch("services.genai.GenerativeModel", return_value=mock_model)
        mocker.patch("streamlit.error")  # st.error の呼び出しを無効化

        result = analyze_meal_with_gemini("テスト食品", "gemini-flash")

        assert result is None

    def test_missing_keys_default_to_zero(self, mocker):
        """JSONキーが一部欠けていても 0 として扱われること"""
        mock_response = MagicMock()
        mock_response.text = '{"cal": 300}'  # p, f, c, 微量栄養素 が欠落
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mocker.patch("services.genai.GenerativeModel", return_value=mock_model)

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
