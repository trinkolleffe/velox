# === path: generate_mappe_province.py ===

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
MARKER_IMAGE_PATH = "autovelox-icon.png"  # https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png
OUTPUT_FOLDER = "output_maps/marker"
ZOOM_MODE = "marker"  # "marker" per ritagliare sui marker, "provincia" per mappa intera
# OUTPUT_FOLDER = "output_maps/provincia"
# ZOOM_MODE = "provincia"  # "marker" per ritagliare sui marker, "provincia" per mappa intera

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# === Funzione per visualizzare marker personalizzati ===
def imscatter(x, y, ax, zoom=0.015, image_path="autovelox-icon.png"):
    if not os.path.exists(image_path):
        print(f"[!] Icona marker non trovata: {image_path}")
        return
    img = plt.imread(image_path)
    im = OffsetImage(img, zoom=zoom)
    for xi, yi in zip(x, y):
        ab = AnnotationBbox(im, (xi, yi), frameon=False, xycoords='data', box_alignment=(0.5, 0), zorder=10)
        ax.add_artist(ab)


# === Carica confini provinciali ===
province_gdf = gpd.read_file(GEOJSON_PATH)

# === Cicla su ogni provincia ===
for _, provincia in province_gdf.iterrows():
    nome_provincia = provincia['prov_name'].lower()
    print(f"\nElaborazione: {nome_provincia.title()}")

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
    provincia_gdf = gpd.GeoDataFrame([provincia], crs=province_gdf.crs)
    provincia_webmerc = provincia_gdf.to_crs(epsg=3857)
    gdf_webmerc = gdf.to_crs(epsg=3857)

    if ZOOM_MODE == "marker":
        bounds = gdf_webmerc.total_bounds
        margin_factor = 0.15  # margine aumentato se si basa solo sui marker
    else:
        bounds = provincia_webmerc.total_bounds
        margin_factor = 0.05

    xmin, ymin, xmax, ymax = bounds
    x_margin = (xmax - xmin) * margin_factor
    y_margin = (ymax - ymin) * margin_factor

    # Calcola livello di zoom dinamico
    width_m = xmax - xmin

    if width_m < 10_000:
        basemap_zoom = 15
    elif width_m < 20_000:
        basemap_zoom = 14
    elif width_m < 40_000:
        basemap_zoom = 13
    else:
        basemap_zoom = 11

    print(f"  [i] Zoom livello OSM usato: {basemap_zoom}")

    # Calcola zoom marker inversamente proporzionale allo zoom della mappa
    marker_zoom = 0.015 * (11 / basemap_zoom)
    print(f"  [i] Zoom marker usato: {marker_zoom:.5f}")

    fig, ax = plt.subplots(figsize=(8.75, 8.75))
    imscatter(gdf_webmerc.geometry.x.values, gdf_webmerc.geometry.y.values, ax=ax, zoom=marker_zoom,
              image_path=MARKER_IMAGE_PATH)
    provincia_webmerc.boundary.plot(ax=ax, color='black', linewidth=0.25, zorder=1)

    ax.set_xlim(xmin - x_margin, xmax + x_margin)
    ax.set_ylim(ymin - y_margin, ymax + y_margin)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_webmerc.crs.to_string(), attribution_size=2,
                    zoom=basemap_zoom)
    ax.set_axis_off()

    output_path = os.path.join(OUTPUT_FOLDER, f"{nome_provincia}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    print(f"  [+] Salvata: {output_path}")
