"""
charts.py のユニットテスト

create_summary_chart は plotly のみに依存する純粋関数なのでモック不要。
"""
import pytest
import plotly.graph_objects as go
from charts import create_summary_chart


# 標準的なテスト用データ
SAMPLE_DATA = {
    "Cal": {"current": 1500, "target": 2000, "unit": "kcal"},
    "P":   {"current": 80,   "target": 100,  "unit": "g"},
    "F":   {"current": 40,   "target": 60,   "unit": "g"},
    "C":   {"current": 200,  "target": 250,  "unit": "g"},
}


class TestCreateSummaryChart:
    """create_summary_chart: グラフ生成ロジックを検証"""

    def test_returns_plotly_figure(self):
        """戻り値が plotly.graph_objects.Figure であること"""
        fig = create_summary_chart(SAMPLE_DATA)
        assert isinstance(fig, go.Figure)

    def test_has_minimum_traces(self):
        """通常時: トラックバーと進捗バーの最低2トレースが存在すること"""
        fig = create_summary_chart(SAMPLE_DATA)
        assert len(fig.data) >= 2

    def test_over_target_adds_excess_trace(self):
        """超過時: 超過バー用の追加トレースが存在すること"""
        over_data = {
            "Cal": {"current": 2500, "target": 2000, "unit": "kcal"},
            "P":   {"current": 80,   "target": 100,  "unit": "g"},
            "F":   {"current": 40,   "target": 60,   "unit": "g"},
            "C":   {"current": 200,  "target": 250,  "unit": "g"},
        }
        fig = create_summary_chart(over_data)
        # トレース数が増えていること（track + normal + excess + labels = 4以上）
        assert len(fig.data) >= 3

    def test_zero_target_no_division_by_zero(self):
        """target=0 でも ZeroDivisionError が発生しないこと"""
        zero_target_data = {
            "Cal": {"current": 100, "target": 0, "unit": "kcal"},
            "P":   {"current": 50,  "target": 0, "unit": "g"},
            "F":   {"current": 30,  "target": 0, "unit": "g"},
            "C":   {"current": 100, "target": 0, "unit": "g"},
        }
        fig = create_summary_chart(zero_target_data)
        assert isinstance(fig, go.Figure)

    def test_all_zeros_does_not_raise(self):
        """current/target がすべてゼロでも例外が発生しないこと"""
        all_zero = {
            "Cal": {"current": 0, "target": 0, "unit": "kcal"},
            "P":   {"current": 0, "target": 0, "unit": "g"},
            "F":   {"current": 0, "target": 0, "unit": "g"},
            "C":   {"current": 0, "target": 0, "unit": "g"},
        }
        fig = create_summary_chart(all_zero)
        assert isinstance(fig, go.Figure)

    def test_layout_has_transparent_background(self):
        """背景が透明に設定されていること"""
        fig = create_summary_chart(SAMPLE_DATA)
        assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"

    def test_figure_height(self):
        """グラフの高さが設定されていること"""
        fig = create_summary_chart(SAMPLE_DATA)
        assert fig.layout.height == 230

    def test_annotations_count_matches_labels(self):
        """アノテーション数がラベル数（=4）と一致すること"""
        fig = create_summary_chart(SAMPLE_DATA)
        # Cal/P/F/C の4項目 → 4つのアノテーション
        assert len(fig.layout.annotations) == 4
