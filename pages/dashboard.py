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
ORANGE = "#F97316"
BLUE = "#3B82F6"
YELLOW = "#EAB308"
GREEN = "#22C55E"
RED = "#FF5252"
DEFAULT_USER_ID = "d8875444-a88a-4a31-947d-2174eefb80f0"


# --- データ取得 ---
@st.cache_data(ttl=120)
def fetch_meal_logs_range(_supabase, user_id: str, start_date: str, end_date: str):
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


# --- グラフ ---
def create_calorie_chart(df, target_cal):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["label"], y=df["calorie"],
        marker_color=ORANGE, name="カロリー", marker_line_width=0,
    ))
    fig.add_hline(
        y=target_cal, line_dash="dash", line_color=RED,
        annotation_text=f"目標 {target_cal}kcal",
        annotation_position="top right",
        annotation_font=dict(color=RED, size=11),
    )
    fig.update_layout(
        height=240, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=10)),
        showlegend=False,
    )
    return fig


def create_pfc_chart(df, target_p=0, target_f=0):
    fig = go.Figure()
    colors = {"protein": BLUE, "fat": YELLOW, "carb": GREEN}
    names = {"protein": "タンパク質", "fat": "脂質", "carb": "炭水化物"}
    for key in ["protein", "fat", "carb"]:
        fig.add_trace(go.Bar(
            x=df["label"], y=df[key],
            marker_color=colors[key], name=names[key], marker_line_width=0,
        ))
    # P目標ライン
    if target_p > 0:
        fig.add_hline(
            y=target_p, line_dash="dash", line_color=BLUE,
            annotation_text=f"P目標 {target_p}g",
            annotation_position="top right",
            annotation_font=dict(color=BLUE, size=11),
        )
    # F目標ライン
    if target_f > 0:
        fig.add_hline(
            y=target_f, line_dash="dash", line_color=YELLOW,
            annotation_text=f"F目標 {target_f}g",
            annotation_position="bottom right",
            annotation_font=dict(color=YELLOW, size=11),
        )
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=10)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11)),
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
logs = fetch_meal_logs_range(supabase, user_id, start.isoformat(), today.isoformat())
df = aggregate_daily(logs, start, days)

days_with_data = int((df["meal_count"] > 0).sum())
total_meals = int(df["meal_count"].sum())
df_active = df[df["meal_count"] > 0]
avg_cal = int(df_active["calorie"].mean()) if days_with_data > 0 else 0
avg_p = int(df_active["protein"].mean()) if days_with_data > 0 else 0
avg_f = int(df_active["fat"].mean()) if days_with_data > 0 else 0
avg_c = int(df_active["carb"].mean()) if days_with_data > 0 else 0

st.caption(f"{days_with_data}日間のデータ · {total_meals}食記録 · 平均 {avg_cal:,} kcal/日（P:{avg_p}g F:{avg_f}g C:{avg_c}g）")

# --- カロリー推移 ---
st.subheader("🔥 日次カロリー推移")
st.plotly_chart(create_calorie_chart(df, target_cal),
                use_container_width=True, config={"staticPlot": True})

# --- PFC推移 ---
st.subheader("🏋️ PFCバランス推移 (g)")
st.plotly_chart(create_pfc_chart(df, target_p, target_f),
                use_container_width=True, config={"staticPlot": True})
