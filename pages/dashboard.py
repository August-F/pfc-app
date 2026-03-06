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
                print(f"[fetch_meal_logs_range] データ取得エラー: {e}")
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
        marker_color="rgba(0,172,193,0.45)", name="カロリー", marker_line_width=0,
    ))
    # カロリー平均/移動平均
    df_active = df[df["meal_count"] > 0]
    if len(df) > 14:
        # 30日間: 7日移動平均
        cal_series = df["calorie"].replace(0, float("nan")).where(df["meal_count"] > 0)
        cal_ma = cal_series.rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["label"], y=cal_ma,
            mode="lines", line=dict(color=TEAL, width=2.5),
            name="移動平均(7日)", connectgaps=True,
        ))
    elif len(df) > 7:
        # 14日間: 3日移動平均
        cal_series = df["calorie"].replace(0, float("nan")).where(df["meal_count"] > 0)
        cal_ma = cal_series.rolling(3, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["label"], y=cal_ma,
            mode="lines", line=dict(color=TEAL, width=2.5),
            name="移動平均(3日)", connectgaps=True,
        ))
    elif len(df_active) > 0:
        # 7日間: 期間全体の平均
        avg_cal_val = df_active["calorie"].mean()
        fig.add_hline(
            y=avg_cal_val, line_dash="solid", line_color=TEAL, line_width=2,
            annotation_text=f"平均 {int(avg_cal_val)}kcal",
            annotation_position="top right",
            annotation_font=dict(color=BLACK, size=10),
        )
    fig.add_hrect(y0=0, y1=target_cal,
                  fillcolor="rgba(0,172,193,0.10)", line_width=0, layer="below")
    fig.add_hline(
        y=target_cal, line_dash="solid",
        line_color="rgba(0,172,193,0.5)", line_width=1,
        annotation_text=f"目標 {target_cal}kcal",
        annotation_position="top left",
        annotation_font=dict(color=BLACK, size=11),
    )
    fig.update_layout(
        height=200, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=AXIS_FONT),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=AXIS_FONT),
        showlegend=len(df) > 7,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color=BLACK)),
    )
    return fig


def create_nutrient_chart(df, key, label, bar_color, line_color, target=0):
    """P・F・C それぞれ個別のグラフを生成する共通関数"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["label"], y=df[key],
        marker_color=bar_color, name=label, marker_line_width=0,
    ))
    df_active = df[df["meal_count"] > 0]
    if len(df_active) > 0:
        if len(df) > 14:
            series = df[key].replace(0, float("nan")).where(df["meal_count"] > 0)
            ma = series.rolling(7, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df["label"], y=ma,
                mode="lines", line=dict(color=line_color, width=2.5),
                name="移動平均(7日)", connectgaps=True,
            ))
        elif len(df) > 7:
            series = df[key].replace(0, float("nan")).where(df["meal_count"] > 0)
            ma = series.rolling(3, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df["label"], y=ma,
                mode="lines", line=dict(color=line_color, width=2.5),
                name="移動平均(3日)", connectgaps=True,
            ))
        else:
            avg_val = df_active[key].mean()
            fig.add_hline(
                y=avg_val, line_dash="solid", line_color=line_color, line_width=2,
                annotation_text=f"平均 {int(avg_val)}g",
                annotation_position="top right",
                annotation_font=dict(color=BLACK, size=10),
            )
    if target > 0:
        fig.add_hrect(y0=0, y1=target, fillcolor=bar_color.replace("0.45", "0.10").replace("0.35", "0.10"),
                      line_width=0, layer="below")
        fig.add_hline(
            y=target, line_dash="solid",
            line_color=line_color, line_width=1,
            annotation_text=f"目標 {target}g",
            annotation_position="top left",
            annotation_font=dict(color=BLACK, size=11),
        )
    fig.update_layout(
        height=180, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=AXIS_FONT),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=AXIS_FONT),
        showlegend=len(df) > 7,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color=BLACK)),
    )
    return fig



# =========================================================
# メイン
# =========================================================
if "user" in st.session_state:
    user_id = st.session_state["user"].id
else:
    user_id = DEFAULT_USER_ID

profile = get_user_profile(user_id)
target_cal = profile.get("target_calories") or 2000
target_p   = profile.get("target_p") or 100
target_f   = profile.get("target_f") or 60
target_c   = profile.get("target_c") or 250

st.title("📊 PFCダッシュボード")

# --- コントロール ---
days = st.radio("表示期間", [7, 14, 30], index=0, horizontal=True,
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

# --- PFC推移（個別グラフ） ---
st.subheader("🏋️ PFC推移 (g)")
st.caption("タンパク質 (P)")
st.plotly_chart(
    create_nutrient_chart(df, "protein", "タンパク質", "rgba(0,172,193,0.45)", TEAL, target_p),
    use_container_width=True, config={"staticPlot": True},
)
st.caption("脂質 (F)")
st.plotly_chart(
    create_nutrient_chart(df, "fat", "脂質", "rgba(255,82,82,0.45)", PINK, target_f),
    use_container_width=True, config={"staticPlot": True},
)
st.caption("炭水化物 (C)")
st.plotly_chart(
    create_nutrient_chart(df, "carb", "炭水化物", "rgba(85,85,85,0.35)", GREY_DARK, target_c),
    use_container_width=True, config={"staticPlot": True},
)

# --- カロリー推移 ---
st.subheader("🔥 日次カロリー推移")
st.plotly_chart(create_calorie_chart(df, target_cal),
                use_container_width=True, config={"staticPlot": True})
