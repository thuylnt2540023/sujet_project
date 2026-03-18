"""
Chart: Download time vs Number of Sources for The Godfather - Home Movies.mkv (188 MB)
Split by Compression, with lines per Fragment Size.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

CSV_PATH = "by_file/The Godfather - Home Movies.csv"
df = pd.read_csv(CSV_PATH)

# Deduplicate
dedup_cols = [
    "timestamp", "daemon_ip", "file_size_bytes",
    "fragment_size_bytes", "sources_used", "compression",
    "total_time_ms", "avg_speed_KB_s",
]
df = df.drop_duplicates(subset=dedup_cols, keep="first").copy()
df["total_time_s"] = df["total_time_ms"] / 1000
df["frag_KB"] = df["fragment_size_bytes"] // 1024

# Aggregate
stats = df.groupby(["sources_used", "frag_KB", "compression"])["total_time_s"] \
          .agg(["mean", "count"]).reset_index()
stats.columns = ["sources", "frag_KB", "compression", "mean_time", "n"]

# --- Colors ---
frag_sizes = sorted(df["frag_KB"].unique())
colors = {128: "#e74c3c", 256: "#e67e22", 512: "#2ecc71", 1024: "#3498db", 2048: "#9b59b6"}
markers = {128: "s", 256: "D", 512: "o", 1024: "^", 2048: "v"}

# --- Plot ---
plt.rcParams.update({"figure.dpi": 150, "font.size": 11})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

for ax, comp_val, title in [
    (ax1, False, "No Compression"),
    (ax2, True, "Compression ON"),
]:
    subset = stats[stats["compression"] == comp_val]
    for frag in frag_sizes:
        frag_data = subset[subset["frag_KB"] == frag].sort_values("sources")
        if frag_data.empty:
            continue
        ax.plot(
            frag_data["sources"], frag_data["mean_time"],
            marker=markers[frag], color=colors[frag],
            linewidth=2, markersize=8,
            label=f"{frag} KB",
        )
        for _, row in frag_data.iterrows():
            ax.annotate(
                f"{row['mean_time']:.0f}s (n={int(row['n'])})",
                xy=(row["sources"], row["mean_time"]),
                textcoords="offset points", xytext=(6, 8),
                fontsize=7.5, color=colors[frag],
            )

    ax.set_xlabel("Number of Sources", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_xticks(sorted(df["sources_used"].unique()))
    ax.legend(title="Fragment Size", fontsize=9, title_fontsize=10, loc="upper right")

ax1.set_ylabel("Avg Download Time (seconds)", fontsize=12)

fig.suptitle(
    "The Godfather - Home Movies (188 MB) -- Download Time vs Sources & Fragment Size",
    fontsize=14, fontweight="bold", y=1.02,
)

plt.tight_layout()
out = "godfather_home_sources_vs_time.png"
plt.savefig(out, bbox_inches="tight")
print(f"Saved: {out}")
plt.show()
