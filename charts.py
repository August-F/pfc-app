import plotly.graph_objects as go

# --- カラー定数 ---
TEAL = "#00ACC1"
TEAL_LIGHT = "rgba(0, 172, 193, 0.15)"
RED = "#FF5252"
TEXT_COLOR = "#111"


def create_summary_chart(data_dict):
    """
    B案デザインの達成率グラフを作成（Plotly版）
    - プログレスバー形式（トラック＋進捗の2層構造）
    - 超過時はバー2分割（通常色＋赤）＋吹き出し＋100%マーカー
    - 左側に円形ラベル
    - 背景透過

    data_dict = {
        'Cal': {'current': 673, 'target': 1210, 'unit': 'kcal'},
        'P':   {'current': 59,  'target': 90,   'unit': 'g'},
        ...
    }

    Returns: plotly.graph_objects.Figure
    """
    labels = list(data_dict.keys())
    # 上からCal, P, F, Cの順 → Plotlyも下から描画するので逆順
    labels.reverse()

    n = len(labels)
    y_pos = list(range(n))

    # --- データの準備 ---
    ratios = []
    value_texts = []

    for label in labels:
        d = data_dict[label]
        tgt = d["target"] if d["target"] > 0 else 1
        ratio = (d["current"] / tgt) * 100
        ratios.append(ratio)
        value_texts.append(f"{int(d['current'])} / {int(d['target'])} {d['unit']}")

    max_ratio = max(ratios) if ratios else 0
    x_display_max = max(max_ratio, 100)
    x_max = x_display_max + max(x_display_max * 0.45, 50)

    bar_width = 0.50

    fig = go.Figure()

    # ============================================================
    # 1) トラックバー（背景レール）— 常に100%幅
    # ============================================================
    fig.add_trace(go.Bar(
        y=y_pos,
        x=[100] * n,
        orientation="h",
        marker=dict(color=TEAL_LIGHT, line=dict(width=0)),
        width=bar_width,
        showlegend=False,
        hoverinfo="none",
    ))

    # ============================================================
    # 2) 通常の進捗バー — min(ratio, 100) 幅
    # ============================================================
    normal_vals = [min(r, 100) for r in ratios]
    fig.add_trace(go.Bar(
        y=y_pos,
        x=normal_vals,
        orientation="h",
        marker=dict(color=TEAL, line=dict(width=0)),
        width=bar_width,
        showlegend=False,
        hoverinfo="none",
    ))

    # ============================================================
    # 3) 超過バー — 100%を超えた部分を赤で表示
    # ============================================================
    excess_vals = [max(r - 100, 0) for r in ratios]
    has_excess = any(v > 0 for v in excess_vals)
    if has_excess:
        fig.add_trace(go.Bar(
            y=y_pos,
            x=excess_vals,
            orientation="h",
            base=[100] * n,
            marker=dict(
                color=[RED if v > 0 else "rgba(0,0,0,0)" for v in excess_vals],
                line=dict(width=0),
            ),
            width=bar_width,
            showlegend=False,
            hoverinfo="none",
        ))

    # ============================================================
    # 4) 左側の円形ラベル（Cal, P, F, C）
    # ============================================================
    fig.add_trace(go.Scatter(
        x=[-8] * n,
        y=y_pos,
        mode="markers+text",
        marker=dict(size=28, color=TEAL, line=dict(width=0)),
        text=labels,
        textfont=dict(color="white", size=9, family="Arial Black, Arial, sans-serif"),
        textposition="middle center",
        showlegend=False,
        hoverinfo="none",
        cliponaxis=False,
    ))

    # ============================================================
    # 5) アノテーション（右側テキスト、吹き出し）& シェイプ（100%線）
    # ============================================================
    annotations = []
    shapes = []

    for i, (label, ratio, vtext) in enumerate(zip(labels, ratios, value_texts)):
        bar_end = max(ratio, normal_vals[i])

        # --- 右側の数値テキスト ---
        if ratio > 100:
            display_text = f"{vtext}  <b>({int(ratio)}%)</b>"
            text_color = TEXT_COLOR
        else:
            display_text = vtext
            text_color = TEXT_COLOR

        annotations.append(dict(
            x=bar_end + 2,
            y=y_pos[i],
            text=display_text,
            showarrow=False,
            font=dict(size=11, color=text_color),
            xanchor="left",
            yanchor="middle",
        ))

        # --- 超過時の装飾 ---
        if ratio > 100:
            # 吹き出し（赤いバブル）
            annotations.append(dict(
                x=ratio,
                y=y_pos[i],
                text=f"<b>{int(ratio)}%</b>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor=RED,
                font=dict(size=9, color="white"),
                bgcolor=RED,
                bordercolor=RED,
                borderwidth=1,
                borderpad=4,
                ax=0,
                ay=-30,
            ))

            # 100%地点の区切り線
            shapes.append(dict(
                type="line",
                x0=100,
                x1=100,
                y0=y_pos[i] - bar_width / 2,
                y1=y_pos[i] + bar_width / 2,
                line=dict(color="#555", width=1, dash="dot"),
            ))


    # ============================================================
    # 6) レイアウト
    # ============================================================
    fig.update_layout(
        barmode="overlay",
        template="none",
        height=230,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            visible=False,
            range=[-16, x_max],
            fixedrange=True,
        ),
        yaxis=dict(
            visible=False,
            range=[-0.6, n - 0.4],
            fixedrange=True,
        ),
        annotations=annotations,
        shapes=shapes,
    )

    return fig
