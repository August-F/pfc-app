"""
pytest 共通設定・フィクスチャ
"""
import sys
import os

# プロジェクトルートを sys.path に追加（pytest.ini の pythonpath と重複するが念のため）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
