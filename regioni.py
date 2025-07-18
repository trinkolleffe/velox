import os
import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import pandas as pd
import numpy as np

# === Costanti ===
GEOJSON_PATH = "regioni.geojson"
DATA_FOLDER = "dati_marker"
OUTPUT_FOLDER = "output_maps"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Carica confini provinciali ===
regioni_gdf = gpd.read_file(GEOJSON_PATH)

# === Cicla su ogni provincia ===
for _, regione in regioni_gdf.iterrows():
    nome_regione = regione['reg_name'].lower()
    print(f"\nElaborazione: {nome_regione.title()}")

    # === Verifica esistenza file marker ===
    csv_path = os.path.join(DATA_FOLDER, f"{nome_regione}.csv")
    json_path = os.path.join(DATA_FOLDER, f"{nome_regione}.json")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    elif os.path.exists(json_path):
        df = pd.read_json(json_path)
    else:
        print(f"  [!] Nessun file marker trovato per {nome_regione}, salto...")
        continue

    if not {'latitude', 'longitude'}.issubset(df.columns):
        print(f"  [!] File marker mancante colonne 'latitude' o 'longitude', salto...")
        continue

    # === Crea GeoDataFrame marker ===
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # === Estrai e proietta confine regione ===
    regione_gdf = gpd.GeoDataFrame([regione], crs=regioni_gdf.crs)
    regione_webmerc = regione_gdf.to_crs(epsg=3857)
    gdf_webmerc = gdf.to_crs(epsg=3857)

    # === Bounding box ===
    combined = gpd.GeoSeries(pd.concat([gdf_webmerc.geometry, regione_webmerc.geometry], ignore_index=True))
    xmin, ymin, xmax, ymax = combined.total_bounds

    # === Plotta ===
    fig, ax = plt.subplots(figsize=(10, 10))
    gdf_webmerc.plot(ax=ax, color='red', markersize=50, edgecolor='black', zorder=3)
    regione_webmerc.boundary.plot(ax=ax, color='black', linewidth=2, zorder=4)

    ax.set_xlim(xmin - 5000, xmax + 5000)
    ax.set_ylim(ymin - 5000, ymax + 5000)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_webmerc.crs.to_string(), zoom=11)

    ax.set_title(f"regione {nome_regione.title()}")
    ax.set_axis_off()

    output_path = os.path.join(OUTPUT_FOLDER, f"{nome_regione}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  [+] Salvata: {output_path}")