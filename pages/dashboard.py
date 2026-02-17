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
def create_calorie_chart(df, target_cal, chart_type):
    fig = go.Figure()
    if chart_type == "棒グラフ":
        fig.add_trace(go.Bar(
            x=df["label"], y=df["calorie"],
            marker_color=ORANGE, name="カロリー", marker_line_width=0,
        ))
    elif chart_type == "エリア":
        fig.add_trace(go.Scatter(
            x=df["label"], y=df["calorie"],
            fill="tozeroy", mode="lines",
            line=dict(color=ORANGE, width=2.5),
            fillcolor="rgba(249, 115, 22, 0.15)", name="カロリー",
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df["label"], y=df["calorie"],
            mode="lines+markers",
            line=dict(color=ORANGE, width=2.5),
            marker=dict(size=6, color=ORANGE), name="カロリー",
        ))
    fig.add_hline(
        y=target_cal, line_dash="dash", line_color=RED,
        annotation_text=f"目標 {target_cal}kcal",
        annotation_position="top right",
        annotation_font=dict(color=RED, size=11),
    )
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=10)),
        showlegend=False,
    )
    return fig


def create_pfc_chart(df, chart_type):
    fig = go.Figure()
    colors = {"protein": BLUE, "fat": YELLOW, "carb": GREEN}
    names = {"protein": "タンパク質", "fat": "脂質", "carb": "炭水化物"}
    for key in ["protein", "fat", "carb"]:
        if chart_type == "棒グラフ":
            fig.add_trace(go.Bar(
                x=df["label"], y=df[key],
                marker_color=colors[key], name=names[key], marker_line_width=0,
            ))
        elif chart_type == "エリア":
            fig.add_trace(go.Scatter(
                x=df["label"], y=df[key],
                fill="tozeroy", mode="lines",
                line=dict(color=colors[key], width=2), name=names[key],
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df["label"], y=df[key],
                mode="lines+markers",
                line=dict(color=colors[key], width=2),
                marker=dict(size=5), name=names[key],
            ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=10)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11)),
        barmode="group" if chart_type == "棒グラフ" else None,
    )
    return fig


def create_pfc_pie(today_row):
    p_cal, f_cal, c_cal = today_row["p_cal"], today_row["f_cal"], today_row["c_cal"]
    if p_cal + f_cal + c_cal == 0:
        return None
    fig = go.Figure(data=[go.Pie(
        labels=["タンパク質", "脂質", "炭水化物"],
        values=[p_cal, f_cal, c_cal],
        marker=dict(colors=[BLUE, YELLOW, GREEN]),
        hole=0.55, textinfo="percent", textfont=dict(size=13),
        hovertemplate="%{label}: %{value} kcal<extra></extra>",
    )])
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=11)),
    )
    return fig


def create_stacked_cal_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["label"], y=df["p_cal"], name="P (kcal)", marker_color=BLUE, marker_line_width=0))
    fig.add_trace(go.Bar(x=df["label"], y=df["f_cal"], name="F (kcal)", marker_color=YELLOW, marker_line_width=0))
    fig.add_trace(go.Bar(x=df["label"], y=df["c_cal"], name="C (kcal)", marker_color=GREEN, marker_line_width=0))
    fig.update_layout(
        barmode="stack", height=300, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=10)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11)),
    )
    return fig


def render_metric(label, value, unit, target, emoji):
    ratio = (value / target * 100) if target > 0 else 0
    is_over = value > target and target > 0
    bar_color = RED if is_over else TEAL
    bar_width = min(ratio, 100)
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.6); border-radius:12px; padding:14px 16px; border-left:4px solid {bar_color};">
        <div style="font-size:0.78rem; color:#666; margin-bottom:2px;">{emoji} {label}</div>
        <div style="display:flex; align-items:baseline; gap:4px;">
            <span style="font-size:1.6rem; font-weight:700; color:#111;">{int(value):,}</span>
            <span style="font-size:0.8rem; color:#888;">{unit}</span>
        </div>
        <div style="background:rgba(0,0,0,0.08); border-radius:4px; height:6px; margin:6px 0 4px; overflow:hidden;">
            <div style="width:{bar_width}%; height:100%; border-radius:4px; background:{bar_color}; transition:width 0.4s;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#888;">
            <span>目標: {int(target):,} {unit}</span>
            <span style="font-weight:600; color:{bar_color};">{int(ratio)}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


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
col_range, col_chart = st.columns(2)
with col_range:
    days = st.radio("表示期間", [7, 14, 30], index=1, horizontal=True,
                    format_func=lambda d: f"{d}日間", key="dash_range")
with col_chart:
    chart_type = st.radio("グラフ形式", ["棒グラフ", "エリア", "折れ線"],
                          horizontal=True, key="dash_chart")

# --- データ取得 ---
today = date.today()
start = today - timedelta(days=days - 1)
logs = fetch_meal_logs_range(supabase, user_id, start.isoformat(), today.isoformat())
df = aggregate_daily(logs, start, days)

today_row = df.iloc[-1]
days_with_data = int((df["meal_count"] > 0).sum())
total_meals = int(df["meal_count"].sum())
avg_cal = int(df["calorie"].mean()) if len(df) > 0 else 0

st.caption(f"{days_with_data}日間のデータ · {total_meals}食記録 · 平均 {avg_cal:,} kcal/日")

# --- 本日のサマリー ---
st.subheader("📅 本日のサマリー")
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_metric("カロリー", today_row["calorie"], "kcal", target_cal, "🔥")
with c2:
    render_metric("タンパク質", today_row["protein"], "g", target_p, "🥩")
with c3:
    render_metric("脂質", today_row["fat"], "g", target_f, "🧈")
with c4:
    render_metric("炭水化物", today_row["carb"], "g", target_c, "🍚")

# --- カロリー推移 ---
st.subheader("🔥 日次カロリー推移")
st.plotly_chart(create_calorie_chart(df, target_cal, chart_type),
                use_container_width=True, config={"staticPlot": True})

# --- PFC推移 ---
st.subheader("🏋️ PFCバランス推移 (g)")
st.plotly_chart(create_pfc_chart(df, chart_type),
                use_container_width=True, config={"staticPlot": True})

# --- 下段 ---
col_pie, col_stack = st.columns(2)
with col_pie:
    st.subheader("🥧 本日のPFC比率")
    pie_fig = create_pfc_pie(today_row)
    if pie_fig:
        st.plotly_chart(pie_fig, use_container_width=True, config={"staticPlot": True})
    else:
        st.info("本日の記録がありません")
with col_stack:
    st.subheader("⚡ カロリー内訳推移")
    st.plotly_chart(create_stacked_cal_chart(df),
                    use_container_width=True, config={"staticPlot": True})
