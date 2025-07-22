import os
import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import pandas as pd
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# === Costanti ===
GEOJSON_PATH = "province.geojson"
DATA_FOLDER = "dati_marker"
OUTPUT_FOLDER = "output_maps"
MARKER_IMAGE_PATH = "marker-icon.png"  # scaricato da: https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png
MARKER_CACHE = "marker_cache"

os.makedirs(MARKER_CACHE, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)



# === Carica confini provinciali ===
province_gdf = gpd.read_file(GEOJSON_PATH)

# === Cicla su ogni provincia ===
for _, provincia in province_gdf.iterrows():
    nome_provincia = provincia['prov_name'].lower()
    print(f"\nElaborazione: {nome_provincia.title()}")

    # === Verifica esistenza file marker ===
    csv_path = os.path.join(DATA_FOLDER, f"{nome_provincia}.csv")
    json_path = os.path.join(DATA_FOLDER, f"{nome_provincia}.json")
    geojson_path = os.path.join(DATA_FOLDER, f"{nome_provincia}.geojson")

    marker_gdf = None

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if {'latitude', 'longitude'}.issubset(df.columns):
            geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
            marker_gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    elif os.path.exists(json_path):
        try:
            gdf = gpd.read_file(json_path)
            if gdf.geometry.type.eq("Point").all():
                gdf['longitude'] = gdf.geometry.x
                gdf['latitude'] = gdf.geometry.y
                marker_gdf = gdf
        except Exception:
            df = pd.read_json(json_path)
            if {'latitude', 'longitude'}.issubset(df.columns):
                geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
                marker_gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    elif os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        if gdf.geometry.type.eq("Point").all():
            gdf['longitude'] = gdf.geometry.x
            gdf['latitude'] = gdf.geometry.y
            marker_gdf = gdf

    if marker_gdf is None or not {'latitude', 'longitude'}.issubset(marker_gdf.columns):
        print(f"  [!] File marker invalido o mancante colonne, salto...")
        continue

    gdf = marker_gdf

    # === Estrai e proietta confine provincia ===
    provincia_gdf = gpd.GeoDataFrame([provincia], crs=province_gdf.crs)
    provincia_webmerc = provincia_gdf.to_crs(epsg=3857)
    gdf_webmerc = gdf.to_crs(epsg=3857)

    # === Bounding box ===
    combined = gpd.GeoSeries(pd.concat([gdf_webmerc.geometry, provincia_webmerc.geometry], ignore_index=True))
    xmin, ymin, xmax, ymax = combined.total_bounds

    # === Plotta ===
    fig, ax = plt.subplots(figsize=(8.75, 8.75))
    for i, row in gdf_webmerc.iterrows():
        x = row.geometry.x
        y = row.geometry.y

        # Costruisci il path dell’immagine marker corrispondente
        marker_path = os.path.join(DATA_FOLDER, f"marker_{i + 1}.png")

        if not os.path.exists(marker_path):
            # print(f"[!] Marker immagine non trovata: {marker_path}, uso marker default")
            marker_path = MARKER_IMAGE_PATH  # fallback a marker generico

        img = plt.imread(marker_path)
        im = OffsetImage(img, zoom=0.05)  # regola zoom a piacere
        ab = AnnotationBbox(
            im,
            (x, y),
            frameon=False,
            box_alignment=(0.5, 0),  # punta il marker sul punto
            zorder=10
        )
        ax.add_artist(ab)

    provincia_webmerc.boundary.plot(ax=ax, color='black', linewidth=0.25, zorder=1)

    ax.set_xlim(xmin - 1000, xmax + 1000)
    ax.set_ylim(ymin - 1000, ymax + 1000)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_webmerc.crs.to_string(), attribution_size=2, zoom=11)
    ax.set_axis_off()

    output_path = os.path.join(OUTPUT_FOLDER, f"{nome_provincia}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  [+] Salvata: {output_path}")
