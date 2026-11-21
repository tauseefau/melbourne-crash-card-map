import sys
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.colors import LinearSegmentedColormap

d = pd.read_csv("cardmap_grid.csv")
rows, cols = int(d.ROW.max()), int(d.COL.max())
tiles = d[d.TYPE == "tile"]
vmax = max(tiles.INCIDENTS.quantile(0.97), 1)
cmap = LinearSegmentedColormap.from_list("heat", ["#2a4d6b","#2f7f9c","#37a39f","#6cc48f","#f0cb61","#e8863c","#c1392b"])
BG, WATER, ZERO = "#070b10", "#12395a", "#0a1118"

MAP_W = 12.0
sc = MAP_W / (cols + 0.6)
fig = plt.figure(figsize=(MAP_W + 2.4, rows*sc + 1.5), dpi=170)
fig.patch.set_facecolor(BG)

ax = fig.add_axes([0.01, 0.01, MAP_W/(MAP_W+2.4), 1 - 1.1/(rows*sc+1.5)])
ax.set_facecolor(BG)

for _, r in d.iterrows():
    x, y = r.COL, rows - r.ROW + 1          # ROW 1 = north = top
    if r.TYPE == "water":
        # water drawn as a continuous surface, not cards -> reads as the bay
        ax.add_patch(Rectangle((x-0.5, y-0.5), 1.0, 1.0, fc=WATER, ec="none", zorder=1))
        continue
    v = int(r.INCIDENTS)
    fc = ZERO if v == 0 else cmap(min(v/vmax, 1))
    tc = "#5d7186" if v == 0 else ("#08101a" if v > vmax*0.55 else "#ffffff")
    name, val = r.LABEL, f"{v:,}"
    ax.add_patch(FancyBboxPatch((x-0.44, y-0.44), 0.88, 0.88,
        boxstyle="round,pad=0.012,rounding_size=0.09",
        lw=0.3 if v else 0.25, ec=BG if v else "#101a24", fc=fc, zorder=2))
    if name:
        ax.text(x, y+0.13, name, ha="center", va="center", fontsize=2.6, color=tc, alpha=.95, zorder=3)
        ax.text(x, y-0.12, val, ha="center", va="center", fontsize=4.0, color=tc, fontweight="bold", zorder=3)

ax.set_xlim(0.25, cols+0.75); ax.set_ylim(0.25, rows+0.75)
ax.set_aspect("equal"); ax.axis("off")

fig.text(0.012, 0.985, "MELBOURNE ROAD CRASHES BY SUBURB",
         color="#f4f8fb", fontsize=17, fontweight="bold", ha="left", va="top")
fig.text(0.012, 0.958,
         f"One card per suburb, laid out as the map \u00b7 every reported crash 2021\u20132025 \u00b7 "
         f"{int(tiles.INCIDENTS.sum()):,} incidents \u00b7 {len(tiles)} suburbs",
         color="#8fa3b8", fontsize=7.5, ha="left", va="top")

# ---- legend ----
lg = fig.add_axes([MAP_W/(MAP_W+2.4) + 0.02, 0.28, 0.11, 0.46]); lg.axis("off")
lg.set_xlim(0,1); lg.set_ylim(0,1)
lg.text(0, 1.00, "INCIDENTS", color="#8fa3b8", fontsize=7.5, fontweight="bold", va="top")
steps = 40
for i in range(steps):
    lg.add_patch(Rectangle((0.0, 0.40 + 0.52*(i/steps)), 0.20, 0.52/steps, fc=cmap(i/(steps-1)), ec="none"))
lg.text(0.26, 0.92, f"{int(vmax)}", color="#c7d4e0", fontsize=7, va="center")
lg.text(0.26, 0.40, "0", color="#c7d4e0", fontsize=7, va="center")
lg.add_patch(Rectangle((0.0, 0.20), 0.20, 0.07, fc=WATER, ec="none"))
lg.text(0.26, 0.235, "Bay water", color="#8fa3b8", fontsize=6.8, va="center")
lg.add_patch(Rectangle((0.0, 0.08), 0.20, 0.07, fc="#16202b", ec="#101a24", lw=.6))
lg.text(0.26, 0.115, "No crashes", color="#8fa3b8", fontsize=6.8, va="center")

fig.text(0.012, 0.012, "Source: Victoria road crash data (Transport Victoria, CC BY 4.0)  \u00b7  "
         "suburb tiles from Vicmap Admin Locality Boundaries (CC BY 4.0)",
         color="#5d6f82", fontsize=6, ha="left", va="bottom")

plt.savefig(sys.argv[1] if len(sys.argv) > 1 else "cardmap_final.png",
            facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.18)
print("rendered")
