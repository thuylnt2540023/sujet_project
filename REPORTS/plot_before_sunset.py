"""
Chart: Download time vs Fragment Size for
Before.Sunset.2004.720p.BrRip.x264.YIFY.mp4 (600 MB)
Separate by daemon location (Osaka vs Virginia).
"""

import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

CSV_PATH = "by_file/Before.Sunset.2004.720p.BrRip.x264.YIFY.csv"
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

# Check actual fragments downloaded
df["actual_frags"] = df["sources_json"].apply(
    lambda x: sum(s["fragments"] for s in json.loads(x))
)
df["complete"] = df["actual_frags"] == df["total_fragments"]

# Remove partial downloads
df = df[df["complete"]].copy()

# Label daemon location
df["location"] = df["daemon_ip"].map({
    "56.155.81.174": "Osaka (ap-northeast-3)",
    "100.31.121.56": "Virginia (us-east-1)",
})

# --- Colors ---
frag_sizes = sorted(df["frag_KB"].unique())
colors = {128: "#e74c3c", 256: "#e67e22", 512: "#2ecc71", 1024: "#3498db", 2048: "#9b59b6"}
markers = {128: "s", 256: "D", 512: "o", 1024: "^", 2048: "v"}

# --- Plot: 2 subplots by daemon location ---
plt.rcParams.update({"figure.dpi": 150, "font.size": 11})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

locations = ["Osaka (ap-northeast-3)", "Virginia (us-east-1)"]
for ax, loc in zip([ax1, ax2], locations):
    subset = df[df["location"] == loc]
    for frag in frag_sizes:
        frag_data = subset[subset["frag_KB"] == frag].sort_values("sources_used")
        if frag_data.empty:
            continue
        comp_label = ""
        for _, row in frag_data.iterrows():
            comp_label = " (C)" if row["compression"] else ""

        ax.plot(
            frag_data["sources_used"], frag_data["total_time_min"],
            marker=markers[frag], color=colors[frag],
            linewidth=2, markersize=8,
            label=f"{frag} KB",
        )
        for _, row in frag_data.iterrows():
            comp_str = "C" if row["compression"] else "NC"
            ax.annotate(
                f"{row['total_time_min']:.1f}m [{comp_str}]",
                xy=(row["sources_used"], row["total_time_min"]),
                textcoords="offset points", xytext=(8, 4),
                fontsize=7.5, color=colors[frag],
            )

    ax.set_xlabel("Number of Sources", fontsize=12)
    ax.set_title(loc, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_xticks(sorted(df["sources_used"].unique()))
    ax.set_xlim(2, 5)
    ax.legend(title="Fragment Size", fontsize=9, title_fontsize=10, loc="upper left")

ax1.set_ylabel("Download Time (minutes)", fontsize=12)

fig.suptitle(
    "Before Sunset (600 MB) -- Download Time by Location, Sources & Fragment Size\n"
    "[C] = Compressed, [NC] = No Compression  |  Partial downloads removed",
    fontsize=12, fontweight="bold", y=1.04,
)

plt.tight_layout()
out = "before_sunset_sources_vs_time.png"
plt.savefig(out, bbox_inches="tight")
print(f"Saved: {out}")
plt.show()
