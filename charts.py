import matplotlib.pyplot as plt


def create_summary_chart(data_dict):
    """
    あすけん風の達成率比較グラフを作成

    data_dict = {
        'Label': {'current': 100, 'target': 200, 'unit': 'g'},
        ...
    }
    """
    labels = list(data_dict.keys())
    # 上からカロリー、P、F、Cの順に並べたいので逆順にする（barhは下から描画するため）
    labels.reverse()

    # データの準備
    ratios = []
    texts = []
    colors = []

    for label in labels:
        d = data_dict[label]
        # ゼロ除算回避
        tgt = d['target'] if d['target'] > 0 else 1
        ratio = (d['current'] / tgt) * 100
        ratios.append(ratio)

        # 数値テキスト (例: 1500 / 2000 kcal)
        texts.append(f"{int(d['current'])} / {int(d['target'])} {d['unit']}")

        # 色分け (100%超えで赤、それ以外は緑)
        if ratio > 100:
            colors.append("#FF4B4B")   # 赤
        else:
            colors.append("#4CAF50")   # 緑 (あすけん風)

    # 描画
    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # バーの描画
    bars = ax.barh(labels, ratios, color=colors, height=0.6, zorder=3)

    # 目標ライン（100%の位置）
    ax.axvline(100, color='black', linestyle='--', linewidth=1.5, zorder=4)

    # ラベルと数値の表示
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=11, fontweight='bold', color='#333333')

    # バーの右側に数値を表示
    max_ratio = max(max(ratios) if ratios else 0, 120)
    ax.set_xlim(0, max_ratio * 1.35)

    for i, bar in enumerate(bars):
        width = bar.get_width()
        label_text = texts[i]
        ax.text(width + 5, bar.get_y() + bar.get_height() / 2, label_text,
                ha='left', va='center', fontsize=10, color='#333333')

    # X軸の設定
    ax.set_xlabel('Achievement Rate (%)', fontsize=9, color='gray')
    ax.grid(axis='x', linestyle=':', alpha=0.5)

    # 枠線を消す
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False)

    plt.tight_layout()
    return fig
