import os
import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import pandas as pd
import numpy as np

# === Costanti ===
GEOJSON_PATH = "province.geojson"
DATA_FOLDER = "dati_marker"
OUTPUT_FOLDER = "output_maps"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Carica confini provinciali ===
province_gdf = gpd.read_file(GEOJSON_PATH)

# === Cicla su ogni provincia ===
for _, provincia in province_gdf.iterrows():
    nome_provincia = provincia['prov_name'].lower()
    print(f"\nElaborazione: {nome_provincia.title()}")

    # === Verifica esistenza file marker ===
    csv_path = os.path.join(DATA_FOLDER, f"{nome_provincia}.csv")
    json_path = os.path.join(DATA_FOLDER, f"{nome_provincia}.geojson")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    elif os.path.exists(json_path):
        df = pd.read_json(json_path)
    else:
        print(f"  [!] Nessun file marker trovato per {nome_provincia}, salto...")
        continue

    if not {'latitude', 'longitude'}.issubset(df.columns):
        print(f"  [!] File marker mancante colonne 'latitude' o 'longitude', salto...")
        continue

    # === Crea GeoDataFrame marker ===
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # === Estrai e proietta confine provincia ===
    provincia_gdf = gpd.GeoDataFrame([provincia], crs=province_gdf.crs)
    provincia_webmerc = provincia_gdf.to_crs(epsg=3857)
    gdf_webmerc = gdf.to_crs(epsg=3857)

    # === Bounding box ===
    combined = gpd.GeoSeries(pd.concat([gdf_webmerc.geometry, provincia_webmerc.geometry], ignore_index=True))
    xmin, ymin, xmax, ymax = combined.total_bounds

    # === Plotta ===
    fig, ax = plt.subplots(figsize=(8, 8))
    gdf_webmerc.plot(ax=ax, color='red', markersize=15, zorder=1)
    provincia_webmerc.boundary.plot(ax=ax, color='black', linewidth=0.5, zorder=1)

    ax.set_xlim(xmin - 1000, xmax + 1000)
    ax.set_ylim(ymin - 1000, ymax + 1000)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_webmerc.crs.to_string(), attribution_size=4, zoom=11)
    # ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.HOT, crs=gdf_webmerc.crs.to_string(), zoom=11)

    # ax.set_title(f"Provincia di {nome_provincia.title()}")
    ax.set_axis_off()

    output_path = os.path.join(OUTPUT_FOLDER, f"{nome_provincia}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  [+] Salvata: {output_path}")