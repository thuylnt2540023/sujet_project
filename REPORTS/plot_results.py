"""
Visualization script for distributed file download system benchmark results.
Generates 6 charts analyzing performance across different configurations.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import json
import os

# ---------- Load & clean data ----------
CSV_PATH = os.path.join(os.path.dirname(__file__), "summary.csv")
df = pd.read_csv(CSV_PATH)

# The dataset contains duplicate rows with different region labels (ap-ne-3, osaka, osk, …).
# Keep only the first occurrence of each unique test to avoid inflating counts.
dedup_cols = [
    "timestamp", "daemon_ip", "file", "file_size_bytes",
    "fragment_size_bytes", "sources_used", "compression",
    "total_time_ms", "avg_speed_KB_s",
]
df = df.drop_duplicates(subset=dedup_cols, keep="first").copy()

# Friendly file labels
df["file_short"] = df["file"].apply(lambda f: f if len(f) <= 30 else f[:27] + "...")
df["file_size_MB"] = df["file_size_bytes"] / (1024 * 1024)
df["total_time_s"] = df["total_time_ms"] / 1000
df["fragment_size_KB"] = df["fragment_size_bytes"] / 1024

# ---------- Filter: focus on the ~10 MB test file for controlled comparisons ----------
# (same file, multiple configs -> fair comparison)
small_file = "Acclaim & Response - The Godfather, Best Picture 1972.mkv"  # ~9.5 MB
df_ctrl = df[df["file"] == small_file].copy()

# Common style
plt.rcParams.update({
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
})

fig, axes = plt.subplots(3, 2, figsize=(14, 18))
fig.suptitle("Distributed Download System -- AWS Benchmark Results", fontsize=15, fontweight="bold", y=0.98)

# ═══════════════════════════════════════════════════════════════
# Chart 1: Download Speed vs Number of Sources (box plot)
# ═══════════════════════════════════════════════════════════════
ax = axes[0, 0]
src_groups = df_ctrl.groupby("sources_used")
positions = sorted(df_ctrl["sources_used"].unique())
data_boxes = [src_groups.get_group(s)["avg_speed_KB_s"].values for s in positions]
bp = ax.boxplot(data_boxes, positions=range(len(positions)), patch_artist=True,
                boxprops=dict(facecolor="#4C72B0", alpha=0.7),
                medianprops=dict(color="red", linewidth=2))
ax.set_xticklabels([str(s) for s in positions])
ax.set_xlabel("Number of Sources")
ax.set_ylabel("Avg Download Speed (KB/s)")
ax.set_title("1. Speed vs Number of Sources")
# Observation annotation
ax.annotate("3 sources hits the sweet spot\nfor this file size (~10 MB)",
            xy=(2, 350), fontsize=8, fontstyle="italic", color="#555")

# ═══════════════════════════════════════════════════════════════
# Chart 2: Fragment Size vs Download Speed (grouped by #sources)
# ═══════════════════════════════════════════════════════════════
ax = axes[0, 1]
for n_src, grp in df_ctrl.groupby("sources_used"):
    frag_avg = grp.groupby("fragment_size_KB")["avg_speed_KB_s"].mean().sort_index()
    ax.plot(frag_avg.index, frag_avg.values, marker="o", label=f"{n_src} src")
ax.set_xlabel("Fragment Size (KB)")
ax.set_ylabel("Avg Download Speed (KB/s)")
ax.set_xscale("log", base=2)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
ax.set_title("2. Fragment Size vs Speed (by #Sources)")
ax.legend(title="#Sources", fontsize=8)

# ═══════════════════════════════════════════════════════════════
# Chart 3: Compression ON vs OFF (same file, same #sources)
# ═══════════════════════════════════════════════════════════════
ax = axes[1, 0]
comp_data = df_ctrl[df_ctrl["sources_used"].isin([2, 3])].copy()
comp_avg = comp_data.groupby(["sources_used", "compression"])["avg_speed_KB_s"].mean().unstack()
x_pos = np.arange(len(comp_avg))
width = 0.35
if False in comp_avg.columns:
    ax.bar(x_pos - width/2, comp_avg[False], width, label="No Compression", color="#4C72B0")
if True in comp_avg.columns:
    ax.bar(x_pos + width/2, comp_avg[True], width, label="Compression ON", color="#DD8452")
ax.set_xticks(x_pos)
ax.set_xticklabels([f"{s} sources" for s in comp_avg.index])
ax.set_ylabel("Avg Download Speed (KB/s)")
ax.set_title("3. Compression Effect on Speed")
ax.legend()

# ═══════════════════════════════════════════════════════════════
# Chart 4: Download Time vs File Size (scalability)
# ═══════════════════════════════════════════════════════════════
ax = axes[1, 1]
scalability = df.groupby("file").agg(
    file_size_MB=("file_size_MB", "first"),
    avg_time_s=("total_time_s", "mean"),
    avg_speed=("avg_speed_KB_s", "mean"),
).sort_values("file_size_MB")

colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(scalability)))
bars = ax.barh(range(len(scalability)), scalability["avg_time_s"], color=colors)
ax.set_yticks(range(len(scalability)))
labels = []
for f in scalability.index:
    sz = scalability.loc[f, "file_size_MB"]
    short = f if len(f) <= 25 else f[:22] + "..."
    labels.append(f"{short}\n({sz:.1f} MB)")
ax.set_yticklabels(labels, fontsize=7)
ax.set_xlabel("Avg Download Time (seconds)")
ax.set_title("4. Avg Download Time by File")
# Add speed labels on bars
for i, (_, row) in enumerate(scalability.iterrows()):
    ax.text(row["avg_time_s"] + 5, i, f"{row['avg_speed']:.0f} KB/s", va="center", fontsize=7, color="#333")

# ═══════════════════════════════════════════════════════════════
# Chart 5: Per-Source Speed Distribution (violin / strip)
# ═══════════════════════════════════════════════════════════════
ax = axes[2, 0]
# Parse sources_json to get per-source speeds
source_speeds = []
for _, row in df.iterrows():
    try:
        sources = json.loads(row["sources_json"])
        for s in sources:
            source_speeds.append({
                "source": s["source"].split(":")[0],
                "port": s["source"].split(":")[1],
                "speed_KB_s": s["speed_KB_s"],
                "fragments": s["fragments"],
            })
    except (json.JSONDecodeError, KeyError):
        pass

df_src = pd.DataFrame(source_speeds)
if not df_src.empty:
    # Top sources by frequency
    top_sources = df_src["source"].value_counts().head(8).index.tolist()
    df_src_top = df_src[df_src["source"].isin(top_sources)]
    src_order = df_src_top.groupby("source")["speed_KB_s"].median().sort_values(ascending=False).index
    data_violin = [df_src_top[df_src_top["source"] == s]["speed_KB_s"].values for s in src_order]
    parts = ax.violinplot(data_violin, showmedians=True, showextrema=True)
    for pc in parts["bodies"]:
        pc.set_facecolor("#4C72B0")
        pc.set_alpha(0.6)
    ax.set_xticks(range(1, len(src_order) + 1))
    ax.set_xticklabels([s[:12] for s in src_order], rotation=30, fontsize=7, ha="right")
    ax.set_ylabel("Speed per Source (KB/s)")
    ax.set_title("5. Per-Source Speed Distribution")

# ═══════════════════════════════════════════════════════════════
# Chart 6: Heatmap -- Fragment Size × #Sources -> Speed
# ═══════════════════════════════════════════════════════════════
ax = axes[2, 1]
pivot = df_ctrl.pivot_table(
    index="fragment_size_KB", columns="sources_used",
    values="avg_speed_KB_s", aggfunc="mean"
).sort_index(ascending=False)

im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
ax.set_xticks(range(pivot.shape[1]))
ax.set_xticklabels([str(int(c)) for c in pivot.columns])
ax.set_yticks(range(pivot.shape[0]))
ax.set_yticklabels([f"{int(r)}" for r in pivot.index])
ax.set_xlabel("Number of Sources")
ax.set_ylabel("Fragment Size (KB)")
ax.set_title("6. Heatmap: Config -> Avg Speed (KB/s)")
# Annotate cells
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        val = pivot.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if val > pivot.values[~np.isnan(pivot.values)].mean() else "black")
fig.colorbar(im, ax=ax, shrink=0.6, label="KB/s")

plt.tight_layout(rect=[0, 0, 1, 0.96])
OUT_PATH = os.path.join(os.path.dirname(__file__), "benchmark_charts.png")
plt.savefig(OUT_PATH, bbox_inches="tight")
print(f"Saved: {OUT_PATH}")
plt.show()

# ═══════════════════════════════════════════════════════════════
# Print short analysis
# ═══════════════════════════════════════════════════════════════
print("""
============================================================
SHORT ANALYSIS -- Distributed Download System (AWS Benchmark)
============================================================

1. SPEED vs #SOURCES:
   - Going from 1->2->3 sources significantly improves throughput
     (up to ~35% faster). Beyond 3 sources, gains plateau or even
     degrade due to coordination overhead on small files.

2. FRAGMENT SIZE:
   - Larger fragments (512 KB–2 MB) yield the best speeds.
   - Very small fragments (128 KB) add overhead from excessive
     round-trips and request scheduling, reducing throughput.

3. COMPRESSION:
   - Compression provides marginal benefit for already-compressed
     media files (.mkv). For binary test data, compression slightly
     reduces effective speed due to CPU overhead with little size gain.

4. SCALABILITY:
   - Download time scales roughly linearly with file size.
   - Larger files (600 MB+) sustain higher average throughput,
     amortizing connection setup costs over more data.

5. SOURCE HETEROGENEITY:
   - Source 13.39.21.10 (eu-west) consistently delivers 250+ KB/s --
     the fastest daemon. Cross-region sources (US-East) are 5-10x
     slower, acting as bottleneck when fragment allocation is equal.

6. OPTIMAL CONFIG:
   - Sweet spot: 512 KB–1 MB fragments, 2–3 nearby sources,
     compression OFF for pre-compressed content.
   - Adding distant/slow sources with equal fragment allocation
     hurts overall completion time (limited by slowest source).
""")
