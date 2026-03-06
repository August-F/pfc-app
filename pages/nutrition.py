"""
🥗 栄養成分ページ（静的リファレンス）
主要食品の1食分目安量と PFC を一覧表示します。
"""

import pandas as pd
import streamlit as st

st.title("🥗 栄養成分")
st.caption("主要食品の1食あたりの目安量とカロリー・PFC値")

# ---------------------------------------------------------------------------
# データ定義: (食品名, 目安量, cal, p, f, c)
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        "title": "🍚 主食",
        "items": [
            ("さつまいも", "中1/2本 (100g)", 132, 1.2,  0.2, 31.9),
            ("うどん",     "1玉ゆで (200g)", 210, 5.2,  0.6, 44.8),
            ("雑穀米",     "1膳 (150g)",     245, 4.2,  1.0, 54.0),
            ("白米",       "1膳 (150g)",     252, 3.8,  0.5, 55.7),
            ("そば",       "1玉ゆで (200g)", 264, 9.6,  2.0, 48.0),
            ("パスタ",     "乾麺80g",        299, 10.2, 1.4, 60.0),
        ],
    },
    {
        "title": "🐟🍗🥩 メイン",
        "items": [
            ("🐟 サバ缶（水煮）",     "1缶 (190g)",     291, 39.7, 15.0, 0.6),
            ("🍗 鶏むね肉（皮なし）", "100g",           116, 23.0, 1.9,  0.1),
            ("🥩 豚ヒレ",             "100g",           130, 22.2, 3.7,  0.3),
            ("🥩 牛もも（赤身）",     "100g",           193, 21.3, 10.7, 0.4),
            ("🐟 焼き魚（さば）",     "1切れ (80g)",    248, 20.8, 17.4, 0.1),
            ("🐟 カツオ",             "刺身5切れ (90g)", 95, 20.2, 1.8,  0.1),
            ("🐟 焼き魚（鮭）",       "1切れ (80g)",    150, 19.8,  8.1, 0.1),
            ("🥩 豚ロース",           "1枚 (100g)",     263, 19.3, 19.2, 0.1),
            ("🐟 まぐろ赤身",         "刺身5切れ (80g)", 84, 18.7, 0.8,  0.1),
            ("🥩 合い挽き肉（豚＋牛）", "100g",           272, 17.2, 21.4, 0.3),
            ("🐟 ぶり",               "刺身5切れ (80g)", 178, 17.1, 14.1, 0.2),
            ("🍗 鶏もも肉（皮あり）", "100g",           204, 16.6, 14.2, 0.1),
            ("🐟 サーモン",           "刺身5切れ (80g)", 163, 16.1, 11.9, 0.1),
            ("🐟 えび",               "5尾 (80g)",       68, 15.4, 0.5,  0.1),
            ("🐟 しめさば",           "5切れ (80g)",     200, 14.7, 15.6, 0.3),
            ("🥩 豚バラ",             "100g",           395, 14.4, 35.4, 0.1),
            ("🐟 いか・たこ",         "1/2杯 (80g)",     67, 14.2, 0.8,  0.1),
            ("🐟 ツナ缶（水煮）",     "1缶 (70g)",       52, 11.5, 0.4,  0.1),
        ],
    },
    {
        "title": "🥚 タンパク源（卵・豆腐・乳製品）",
        "items": [
            ("ギリシャヨーグルト", "100g",             59, 10.0,  0.3, 4.0),
            ("卵",                 "M1個 (60g)",       91,  7.4,  6.1, 0.2),
            ("納豆",               "1パック (45g)",     90,  7.4,  4.6, 5.3),
            ("枝豆",               "50g（さやなし）",   68,  5.8,  3.0, 4.6),
            ("豆腐（絹）",         "1/3丁 (100g)",     56,  5.3,  3.0, 2.0),
        ],
    },
]

# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------

def _highlight_pf(row):
    styles = [""] * len(row)
    cols = list(row.index)
    if row["F(g)"] >= 20:
        styles[cols.index("F(g)")] = "background-color: #ffb3ba"
    p_col = "P(g)▲" if "P(g)▲" in cols else "P(g)"
    if row[p_col] >= 20:
        styles[cols.index(p_col)] = "background-color: #c8f5c8"
    return styles


for cat in CATEGORIES:
    show_nutrition = cat.get("show_nutrition", True)
    with st.expander(cat["title"], expanded=True):
        if show_nutrition:
            df = pd.DataFrame(
                cat["items"],
                columns=["食品名", "目安量", "kcal", "P(g)", "F(g)", "C(g)"],
            )
            row_height = 35
            header_height = 38
            tbl_height = len(df) * row_height + header_height
            if "メイン" in cat["title"] or "タンパク源" in cat["title"]:
                df = df.rename(columns={"P(g)": "P(g)▲"})
                fmt = {"kcal": "{:.1f}", "P(g)▲": "{:.1f}", "F(g)": "{:.1f}", "C(g)": "{:.1f}"}
            else:
                df = df.rename(columns={"kcal": "kcal▼"})
                fmt = {"kcal▼": "{:.1f}", "P(g)": "{:.1f}", "F(g)": "{:.1f}", "C(g)": "{:.1f}"}
            if "メイン" in cat["title"]:
                st.dataframe(
                    df.style.apply(_highlight_pf, axis=1).format(fmt),
                    hide_index=True,
                    use_container_width=True,
                    height=tbl_height,
                )
            else:
                st.dataframe(df.style.format(fmt), hide_index=True, use_container_width=True, height=tbl_height)
        else:
            names = [item[0] for item in cat["items"]]
            df = pd.DataFrame(names, columns=["食品名"])
            st.dataframe(df, hide_index=True, use_container_width=True)

st.divider()
st.caption(
    "※ 数値は文部科学省「日本食品標準成分表」および一般的な栄養データをもとにした概算値です。"
    "製品・調理法により異なります。"
)
