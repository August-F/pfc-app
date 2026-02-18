"""
📊 PFCダッシュボードページ
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from config import get_supabase
from services import get_user_profile

supabase = get_supabase()

# --- 定数 ---
TEAL = "#00ACC1"
PINK = "#FF5252"
GREY_DARK = "#555555"
RED = "#FF5252"
DEFAULT_USER_ID = "d8875444-a88a-4a31-947d-2174eefb80f0"


# --- データ取得 ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_meal_logs_range(user_id: str, start_date: str, end_date: str):
    """指定期間の meal_logs を取得（リトライ付き）"""
    import time as _time
    _supabase = get_supabase()
    for attempt in range(3):
        try:
            res = (
                _supabase.table("meal_logs")
                .select("*")
                .eq("user_id", user_id)
                .gte("meal_date", start_date)
                .lte("meal_date", end_date)
                .order("meal_date", desc=False)
                .execute()
            )
            return res.data if res and res.data else []
        except Exception as e:
            if attempt < 2:
                _time.sleep(1)
            else:
                st.error(f"データ取得エラー: {e}")
                return []


def aggregate_daily(logs, start_date, days):
    rows = []
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    for i in range(days):
        d = start_date + timedelta(days=i)
        key = d.isoformat()
        wd = weekdays[d.weekday()]
        rows.append({
            "date": key,
            "label": f"{d.month}/{d.day}({wd})",
            "calorie": 0, "protein": 0, "fat": 0, "carb": 0,
            "p_cal": 0, "f_cal": 0, "c_cal": 0,
            "meal_count": 0,
        })
    date_map = {r["date"]: r for r in rows}
    for log in logs:
        r = date_map.get(log["meal_date"])
        if not r:
            continue
        r["calorie"] += log.get("calories", 0) or 0
        r["protein"] += log.get("p_val", 0) or 0
        r["fat"] += log.get("f_val", 0) or 0
        r["carb"] += log.get("c_val", 0) or 0
        r["p_cal"] += (log.get("p_val", 0) or 0) * 4
        r["f_cal"] += (log.get("f_val", 0) or 0) * 9
        r["c_cal"] += (log.get("c_val", 0) or 0) * 4
        r["meal_count"] += 1
    return pd.DataFrame(rows)


# --- 共通軸スタイル ---
AXIS_FONT = dict(size=10, color="#111")
GRID_COLOR = "rgba(0,0,0,0.08)"
BLACK = "#111"


# --- グラフ ---
def create_calorie_chart(df, target_cal):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["label"], y=df["calorie"],
        marker_color=TEAL, name="カロリー", marker_line_width=0,
    ))
    # 30日間: 7日間移動平均
    if len(df) > 14:
        cal_series = df["calorie"].replace(0, float("nan")).where(df["meal_count"] > 0)
        cal_ma = cal_series.rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["label"], y=cal_ma,
            mode="lines", line=dict(color=TEAL, width=2.5),
            name="移動平均(7日)", connectgaps=True,
        ))
    fig.add_hline(
        y=target_cal, line_dash="dash", line_color=RED,
        annotation_text=f"目標 {target_cal}kcal",
        annotation_position="top right",
        annotation_font=dict(color=BLACK, size=11),
    )
    fig.update_layout(
        height=240, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=AXIS_FONT),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=AXIS_FONT),
        showlegend=len(df) > 14,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color=BLACK)),
    )
    return fig


def create_pfc_chart(df, target_p=0, target_f=0):
    fig = go.Figure()
    colors = {"protein": "rgba(0,172,193,0.45)", "fat": "rgba(255,82,82,0.45)", "carb": "rgba(85,85,85,0.35)"}
    names = {"protein": "タンパク質", "fat": "脂質", "carb": "炭水化物"}
    for key in ["protein", "fat", "carb"]:
        fig.add_trace(go.Bar(
            x=df["label"], y=df[key],
            marker_color=colors[key], name=names[key], marker_line_width=0,
        ))
    # P・F平均ライン
    df_active = df[df["meal_count"] > 0]
    if len(df_active) > 0:
        if len(df) > 14:
            # 30日間: 7日間移動平均（記録なし日は NaN 扱い）
            p_series = df["protein"].replace(0, float("nan")).where(df["meal_count"] > 0)
            f_series = df["fat"].replace(0, float("nan")).where(df["meal_count"] > 0)
            p_ma = p_series.rolling(7, min_periods=1).mean()
            f_ma = f_series.rolling(7, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df["label"], y=p_ma,
                mode="lines", line=dict(color=TEAL, width=2.5),
                name="P移動平均(7日)", connectgaps=True,
            ))
            fig.add_trace(go.Scatter(
                x=df["label"], y=f_ma,
                mode="lines", line=dict(color=PINK, width=2.5),
                name="F移動平均(7日)", connectgaps=True,
            ))
        else:
            # 7・14日間: 期間全体の平均を実線
            avg_p = df_active["protein"].mean()
            fig.add_hline(
                y=avg_p, line_dash="solid", line_color=TEAL, line_width=2,
                annotation_text=f"P平均 {int(avg_p)}g",
                annotation_position="top left",
                annotation_font=dict(color=BLACK, size=10),
            )
            avg_f = df_active["fat"].mean()
            fig.add_hline(
                y=avg_f, line_dash="solid", line_color=PINK, line_width=2,
                annotation_text=f"F平均 {int(avg_f)}g",
                annotation_position="bottom left",
                annotation_font=dict(color=BLACK, size=10),
            )
    # P目標ライン
    if target_p > 0:
        fig.add_hline(
            y=target_p, line_dash="dash", line_color=TEAL,
            annotation_text=f"P目標 {target_p}g",
            annotation_position="top right",
            annotation_font=dict(color=BLACK, size=11),
        )
    # F目標ライン
    if target_f > 0:
        fig.add_hline(
            y=target_f, line_dash="dash", line_color=PINK,
            annotation_text=f"F目標 {target_f}g",
            annotation_position="bottom right",
            annotation_font=dict(color=BLACK, size=11),
        )
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=AXIS_FONT),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=AXIS_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color=BLACK)),
        barmode="group",
    )
    return fig



# =========================================================
# メイン
# =========================================================
if "user" in st.session_state:
    user_id = st.session_state["user"].id
else:
    user_id = DEFAULT_USER_ID

profile = get_user_profile(supabase, user_id)
target_cal = profile.get("target_calories", 2000)
target_p = profile.get("target_p", 100)
target_f = profile.get("target_f", 60)
target_c = profile.get("target_c", 250)

st.title("📊 PFCダッシュボード")

# --- コントロール ---
days = st.radio("表示期間", [7, 14, 30], index=1, horizontal=True,
                format_func=lambda d: f"{d}日間", key="dash_range",
                label_visibility="collapsed")

# --- データ取得 ---
today = date.today()
start = today - timedelta(days=days - 1)
logs = fetch_meal_logs_range(user_id, start.isoformat(), today.isoformat())
df = aggregate_daily(logs, start, days)

days_with_data = int((df["meal_count"] > 0).sum())
total_meals = int(df["meal_count"].sum())
df_active = df[df["meal_count"] > 0]
avg_cal = int(df_active["calorie"].mean()) if days_with_data > 0 else 0
avg_p = int(df_active["protein"].mean()) if days_with_data > 0 else 0
avg_f = int(df_active["fat"].mean()) if days_with_data > 0 else 0
avg_c = int(df_active["carb"].mean()) if days_with_data > 0 else 0

st.caption(f"{days_with_data}日間のデータ · {total_meals}食記録 · 平均 {avg_cal:,} kcal/日  \n（P:{avg_p}g F:{avg_f}g C:{avg_c}g）")

# --- PFC推移 ---
st.subheader("🏋️ PFCバランス推移 (g)")
st.plotly_chart(create_pfc_chart(df, target_p, target_f),
                use_container_width=True, config={"staticPlot": True})

# --- カロリー推移 ---
st.subheader("🔥 日次カロリー推移")
st.plotly_chart(create_calorie_chart(df, target_cal),
                use_container_width=True, config={"staticPlot": True})
