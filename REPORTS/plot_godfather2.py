"""
Chart: Download time vs Number of Sources for Godfather Part 2 (2.7 GB)
Limited data -- only 512 KB fragment, 1/2/4 sources.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

CSV_PATH = "by_file/The.Godfather.Part.2.1974.1080p.BrRip.x264.BOKUTOX.YIFY.csv"
df = pd.read_csv(CSV_PATH)

# Deduplicate
dedup_cols = [
    "timestamp", "daemon_ip", "file_size_bytes",
    "fragment_size_bytes", "sources_used", "compression",
    "total_time_ms", "avg_speed_KB_s",
]
df = df.drop_duplicates(subset=dedup_cols, keep="first").copy()
df["total_time_min"] = df["total_time_ms"] / 1000 / 60
df["frag_KB"] = df["fragment_size_bytes"] // 1024

# Aggregate
stats = df.groupby(["sources_used", "compression"]).agg(
    mean_time=("total_time_min", "mean"),
    mean_speed=("avg_speed_KB_s", "mean"),
    n=("total_time_min", "count"),
).reset_index()

# --- Plot ---
plt.rcParams.update({"figure.dpi": 150, "font.size": 11})
fig, ax = plt.subplots(figsize=(9, 5))

bar_colors = []
labels = []
for _, row in stats.iterrows():
    comp_str = "compressed" if row["compression"] else "no compress"
    labels.append(f"{int(row['sources_used'])} src\n({comp_str})")
    bar_colors.append("#DD8452" if row["compression"] else "#4C72B0")

x = np.arange(len(stats))
bars = ax.bar(x, stats["mean_time"], color=bar_colors, width=0.5, edgecolor="white", alpha=0.85)

# Annotate bars
for i, (bar, (_, row)) in enumerate(zip(bars, stats.iterrows())):
    # Time inside bar
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
            f"{row['mean_time']:.1f} min",
            ha="center", va="center", fontsize=11, color="white", fontweight="bold")
    # Speed + count above bar
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f"{row['mean_speed']:.0f} KB/s  (n={int(row['n'])})",
            ha="center", va="bottom", fontsize=9, color="#333")

ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Avg Download Time (minutes)", fontsize=12)
ax.set_title(
    "The Godfather Part 2 (2.7 GB, 512 KB fragment)\nDownload Time vs Sources",
    fontsize=13, fontweight="bold",
)
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)

# Legend for colors
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor="#4C72B0", label="No Compression"),
                   Patch(facecolor="#DD8452", label="Compression ON")]
ax.legend(handles=legend_elements, fontsize=10)

# Note
ax.annotate(
    "Limited test data: only 512 KB fragment size tested.\n"
    "File is a 2.7 GB video -- only partial download was captured\n"
    "(288 of 5534 fragments in single-source tests).",
    xy=(0.98, 0.95), xycoords="axes fraction",
    fontsize=8, fontstyle="italic", color="#555",
    va="top", ha="right",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
)

plt.tight_layout()
out = "godfather2_sources_vs_time.png"
plt.savefig(out, bbox_inches="tight")
print(f"Saved: {out}")
plt.show()
