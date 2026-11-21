"""Tile-grid cartogram: suburbs as cards, Port Phillip Bay as water, full grid emit."""
import sys, json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

CELL = float(sys.argv[1]) if len(sys.argv) > 1 else 3.2

d = pd.read_csv("subs_joined.csv")

# --- land coverage from the full Vicmap locality layer (it tiles all land) ---
land = gpd.read_file("crash/suburbs_raw.geojson").to_crs("EPSG:3111")
land_union = land.geometry.union_all()

def layout(cell, ring_max=10):
    df = d.assign(GX=np.floor(d.X / cell).astype(int), GY=np.floor(d.Y / cell).astype(int))
    seq = df.sort_values(["GY", "GX"], ascending=[False, True])   # raster order preserves shape
    taken, assign = {}, {}
    for idx, r in seq.iterrows():
        cx, cy = r.GX, r.GY
        if (cx, cy) not in taken:
            assign[idx] = (cx, cy); taken[(cx, cy)] = idx; continue
        placed = False
        for ring in range(1, ring_max + 1):
            cands = [(dx*dx + dy*dy, (cx+dx, cy+dy))
                     for dx in range(-ring, ring+1) for dy in range(-ring, ring+1)
                     if max(abs(dx), abs(dy)) == ring and (cx+dx, cy+dy) not in taken]
            if cands:
                cands.sort(key=lambda t: t[0])
                assign[idx] = cands[0][1]; taken[cands[0][1]] = idx; placed = True; break
        if not placed:
            assign[idx] = (cx, cy)
    res = d.copy()
    res["GX"] = [assign[i][0] for i in res.index]
    res["GY"] = [assign[i][1] for i in res.index]
    res = res.drop_duplicates(["GX", "GY"])
    x0, x1, y0, y1 = res.GX.min(), res.GX.max(), res.GY.min(), res.GY.max()
    res["COL"] = res.GX - x0 + 1
    res["ROW"] = (y1 - res.GY) + 1
    return res, (x0, x1, y0, y1)

res, (x0, x1, y0, y1) = layout(CELL)
rows, cols = int(res.ROW.max()), int(res.COL.max())

def short(name):
    n = name.upper()
    for k, v in {"MOUNT ":"MT ","SOUTH ":"S ","NORTH ":"N ","EAST ":"E ","WEST ":"W "}.items():
        if n.startswith(k): n = v + n[len(k):]
    return n[:11]

res["LABEL"] = res.SUBURB.map(short)
res["TYPE"] = "tile"

# --- complete grid: fill missing cells as water or blank land ---
full = []
for row in range(1, rows + 1):
    for col in range(1, cols + 1):
        gx, gy = x0 + col - 1, y1 - row + 1
        full.append({"ROW": row, "COL": col, "GX": gx, "GY": gy})
skeleton = pd.DataFrame(full)

def land_frac(gx, gy):
    cellpoly = box(gx*CELL*1000, gy*CELL*1000, (gx+1)*CELL*1000, (gy+1)*CELL*1000)
    return cellpoly.intersection(land_union).area / cellpoly.area

have = set(zip(res.ROW, res.COL))
extra = []
for _, s in skeleton.iterrows():
    if (s.ROW, s.COL) in have:
        continue
    lf = land_frac(s.GX, s.GY)
    typ = "water" if lf < 0.18 else "blank"
    extra.append({"ROW": s.ROW, "COL": s.COL, "GX": s.GX, "GY": s.GY, "SUBURB": "",
                  "LABEL": "", "TYPE": typ, "INCIDENTS": 0, "FATALITIES": 0, "SERIOUS": 0,
                  "OTHER_INJ": 0, "X": np.nan, "Y": np.nan})
res["GX"] = res.GX; res["GY"] = res.GY
grid = pd.concat([res, pd.DataFrame(extra)], ignore_index=True)
grid["CELL_TEXT"] = grid.apply(
    lambda r: r.LABEL + "\n" + f"{int(r.INCIDENTS):,}" if r.TYPE == "tile" else "", axis=1)
grid = grid[grid.TYPE != "blank"].sort_values(["ROW", "COL"]).reset_index(drop=True)

# sort key that reverses the "count matters" ordering only for colouring
grid["COLOUR_VALUE"] = np.where(grid.TYPE == "tile", grid.INCIDENTS, np.nan)
grid.to_csv("cardmap_grid.csv", index=False)

counts = grid.TYPE.value_counts().to_dict()
print(f"grid {rows}x{cols} | {counts} | crashes {int(grid.INCIDENTS.sum()):,}")
json.dump({"rows": rows, "cols": cols, "cell_km": CELL, **counts,
           "crashes": int(grid.INCIDENTS.sum())}, open("cardmap_meta.json", "w"), indent=2)
