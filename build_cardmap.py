"""
Build a suburb-level 'card map' of Melbourne road crashes.

Source: Victoria road crash data (Transport Victoria open data, CC BY 4.0)
        Vicmap Admin Locality Boundaries (CC BY 4.0)
Output: cardmap.csv  -> one row per suburb tile (ROW, COL, SUBURB, INCIDENTS)
        preview.png   -> static proof of the layout
"""
import json, math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point, box

YEAR_FROM, YEAR_TO = 2021, 2025
CELL_KM = 2.4

# Greater Melbourne (ABS GCCSA) local government areas
METRO_LGAS = {
    "BANYULE","BAYSIDE","BOROONDARA","BRIMBANK","CARDINIA","CASEY","DAREBIN",
    "FRANKSTON","GLEN EIRA","GREATER DANDENONG","HOBSONS BAY","HUME","KINGSTON",
    "KNOX","MANNINGHAM","MARIBYRNONG","MAROONDAH","MELBOURNE","MELTON","MERRI-BEK",
    "MONASH","MOONEE VALLEY","MORNINGTON PENINSULA","NILLUMBIK","PORT PHILLIP",
    "STONNINGTON","WHITEHORSE","WHITTLESEA","WYNDHAM","YARRA","YARRA RANGES",
}

# ---------- 1. crashes ----------
cols = ["ACCIDENT_NO","ACCIDENT_DATE","LATITUDE","LONGITUDE","LGA_NAME",
        "SEVERITY","FATALITY","SERIOUSINJURY","OTHERINJURY","DEG_URBAN_NAME","SPEED_ZONE"]
df = pd.read_csv("crash/full.csv", usecols=cols, low_memory=False)
df["ACCIDENT_DATE"] = pd.to_datetime(df["ACCIDENT_DATE"], errors="coerce")
df = df[
    df.ACCIDENT_DATE.dt.year.between(YEAR_FROM, YEAR_TO)
    & df.DEG_URBAN_NAME.isin(["MELB_URBAN", "MELBOURNE_CBD"])
    & df.LATITUDE.between(-38.4, -37.4)
    & df.LONGITUDE.between(144.3, 145.8)
].copy()
print(f"crashes in scope: {len(df):,}")

pts = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.LONGITUDE, df.LATITUDE), crs="EPSG:4326"
)

# ---------- 2. suburbs ----------
subs = gpd.read_file("crash/suburbs_raw.geojson")
subs["SUBURB"] = subs["locality_name"].str.strip().str.title()
subs = subs[["SUBURB", "geometry"]].dissolve(by="SUBURB").reset_index()

lga = gpd.read_file("crash/lga.geojson")
lga["lga_name"] = lga["lga_name"].str.upper()
metro_union = lga[lga.lga_name.isin(METRO_LGAS)].geometry.union_all()

# keep suburbs inside Greater Melbourne
subs["_pt4326"] = subs.geometry.representative_point()
subs = subs[subs._pt4326.within(metro_union)].copy()

# project to Vicgrid metres
subs = subs.to_crs("EPSG:3111")
subs["_pt"] = subs.geometry.representative_point()
pts_m = pts.to_crs("EPSG:3111")

# drop the rural fringe: keep suburbs near a cell that actually has crashes
occ = set(zip(np.floor(pts_m.geometry.x/1000).astype(int),
              np.floor(pts_m.geometry.y/1000).astype(int)))
def near_urban(pt, pad=2):
    cx, cy = int(np.floor(pt.x/1000)), int(np.floor(pt.y/1000))
    return any((cx+dx, cy+dy) in occ for dx in range(-pad, pad+1) for dy in range(-pad, pad+1))

subs = subs[subs._pt.map(near_urban)].copy()
print(f"metro suburbs: {len(subs)}")

# ---------- 3. spatial join ----------
j = gpd.sjoin(pts_m, subs[["SUBURB", "geometry"]], how="left", predicate="intersects")
j = j[~j.index.duplicated(keep="first")]
j = j.dropna(subset=["SUBURB"])

agg = j.groupby("SUBURB").agg(
    INCIDENTS=("ACCIDENT_NO", "nunique"),
    FATALITIES=("FATALITY", "sum"),
    SERIOUS=("SERIOUSINJURY", "sum"),
    OTHER_INJ=("OTHERINJURY", "sum"),
).reset_index()

# project suburb points to metres
subs = subs.merge(agg, on="SUBURB", how="left")
for c in ["INCIDENTS","FATALITIES","SERIOUS","OTHER_INJ"]:
    subs[c] = subs[c].fillna(0).astype(int)

subs["X"] = subs._pt.x / 1000.0   # km
subs["Y"] = subs._pt.y / 1000.0
print(f"suburbs matched to >=1 crash: {(subs.INCIDENTS>0).sum()} | total crashes: {subs.INCIDENTS.sum():,}")

# ---------- 4. tile grid cartogram ----------
cell = CELL_KM
gx = np.floor(subs.X / cell).astype(int)
gy = np.floor(subs.Y / cell).astype(int)

taken = {}
assign = {}
order = subs.sort_values(["INCIDENTS", "SUBURB"], ascending=[False, True])
for idx, r in order.iterrows():
    cx, cy = gx[idx], gy[idx]
    best = None
    for ring in range(0, 12):
        cands = []
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                key = (cx + dx, cy + dy)
                if key in taken:
                    continue
                d = (dx * cell) ** 2 + (dy * cell) ** 2
                cands.append((d, key))
        if cands:
            cands.sort(key=lambda t: (t[0], abs(t[1][0]-cx) + abs(t[1][1]-cy)))
            best = cands[0][1]
            break
    taken[best] = r.SUBURB
    assign[r.SUBURB] = best

subs["GX"] = subs.SUBURB.map(lambda s: assign[s][0])
subs["GY"] = subs.SUBURB.map(lambda s: assign[s][1])

# trim empty rows/cols
x0, x1 = subs.GX.min(), subs.GX.max()
y0, y1 = subs.GY.min(), subs.GY.max()
subs = subs[(subs.GX >= x0) & (subs.GX <= x1) & (subs.GY >= y0) & (subs.GY <= y1)].copy()

subs["COL"] = subs.GX - x0 + 1
subs["ROW"] = (y1 - subs.GY) + 1        # north at top
rows, cols = int(subs.ROW.max()), int(subs.COL.max())
print(f"grid: {rows} rows x {cols} cols | tiles: {len(subs)} | fill {len(subs)/(rows*cols):.0%}")

# short label for the tile face
def short(name):
    n = name.upper()
    repl = {"MOUNT ":"MT ", "SOUTH ":"S ", "NORTH ":"N ", "EAST ":"E ", "WEST ":"W "}
    for k, v in repl.items():
        if n.startswith(k):
            n = v + n[len(k):]
    return n[:11]

subs["LABEL"] = subs.SUBURB.map(short)
subs["CELL_TEXT"] = subs.LABEL + "\n" + subs.INCIDENTS.map(lambda v: f"{v:,}")

subs = subs.sort_values(["ROW", "COL"])
out = subs[["ROW","COL","SUBURB","LABEL","CELL_TEXT","INCIDENTS","FATALITIES","SERIOUS","OTHER_INJ","X","Y"]]
out.to_csv("cardmap.csv", index=False)
subs[["SUBURB","INCIDENTS","FATALITIES","SERIOUS","OTHER_INJ","X","Y"]].to_csv("subs_joined.csv", index=False)
print("wrote cardmap.csv")

json.dump({
    "rows": rows, "cols": cols, "cell_km": cell,
    "crashes": int(subs.INCIDENTS.sum()), "tiles": int(len(subs)),
    "years": [YEAR_FROM, YEAR_TO],
}, open("cardmap_meta.json","w"), indent=2)

# ---------- 5. preview ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap

vmax = subs.INCIDENTS.quantile(0.97)
cmap = LinearSegmentedColormap.from_list("heat", ["#1c2b3a","#2c4a63","#2f6f8f","#3fa7b8","#f2c14e","#e8833a","#c0392b"])

fig, ax = plt.subplots(figsize=(cols*0.62, rows*0.62 + 1.0), dpi=170)
fig.patch.set_facecolor("#0e141b"); ax.set_facecolor("#0e141b")
for _, r in subs.iterrows():
    x, y = r.COL, rows - r.ROW + 1
    v = r.INCIDENTS
    c = "#16202b" if v == 0 else cmap(min(v / max(vmax,1), 1.0))
    ax.add_patch(FancyBboxPatch((x-0.46, y-0.46), 0.92, 0.92,
                 boxstyle="round,pad=0.02,rounding_size=0.12",
                 linewidth=0.6, edgecolor="#0e141b", facecolor=c))
    tc = "#5c6b7a" if v == 0 else ("#101820" if v > vmax*0.55 else "#ffffff")
    ax.text(x, y+0.10, r.LABEL, ha="center", va="center", fontsize=3.4,
            color=tc, alpha=0.95 if v else 0.55)
    ax.text(x, y-0.13, f"{v:,}", ha="center", va="center", fontsize=5.2,
            color=tc, fontweight="bold")
ax.set_xlim(0.4, cols+0.6); ax.set_ylim(rows+0.6, 0.4)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title(f"Melbourne road crashes by suburb  |  {YEAR_FROM}\u2013{YEAR_TO}  |  {subs.INCIDENTS.sum():,} incidents",
             color="#e8eef5", fontsize=10, pad=12, loc="left")
plt.tight_layout()
plt.savefig("preview.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
print("wrote preview.png")
