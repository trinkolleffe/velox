# === path: generate_mappe_province.py ===

import os
import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import pandas as pd
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

# === Costanti ===
GEOJSON_PATH = "province.geojson"
DATA_FOLDER = "dati_marker"
OUTPUT_FOLDER = "output_maps"
MARKER_IMAGE_PATH = "autovelox-icon.png"
ZOOM_MODE = "provincia"
TRIM_IMAGE = True
TRIM_MARGIN_PX = 50
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

    bounds = provincia_webmerc.total_bounds
    margin_factor = 0.05

    xmin, ymin, xmax, ymax = bounds
    x_margin = (xmax - xmin) * margin_factor
    y_margin = (ymax - ymin) * margin_factor

    basemap_zoom = 11
    marker_zoom = 0.015
    print(f"  [i] Zoom livello OSM usato: {basemap_zoom}")

    fig, ax = plt.subplots(figsize=(8.75, 8.75))
    imscatter(gdf_webmerc.geometry.x.values, gdf_webmerc.geometry.y.values, ax=ax, zoom=marker_zoom, image_path=MARKER_IMAGE_PATH)
    provincia_webmerc.boundary.plot(ax=ax, color='black', linewidth=0.25, zorder=1)

    ax.set_xlim(xmin - x_margin, xmax + x_margin)
    ax.set_ylim(ymin - y_margin, ymax + y_margin)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_webmerc.crs.to_string(), attribution_size=2, zoom=basemap_zoom)
    ax.set_axis_off()

    output_base = os.path.join(OUTPUT_FOLDER, f"{nome_provincia}")
    output_full = f"{output_base}.full.png"
    output_crop = f"{output_base}.png"

    # === Disegna rettangolo rosso per debug ===
    from matplotlib.patches import Rectangle
    rect = Rectangle(
         (x0, y0), x1 - x0, y1 - y0,
         linewidth=2, edgecolor='red', facecolor='none',
         transform=None  # pixel coordinates
    )
    ax.add_patch(rect)

    plt.savefig(output_full, dpi=300, bbox_inches='tight', pad_inches=0)

    if TRIM_IMAGE:
        img = Image.open(output_full)
        points = np.vstack(ax.transData.transform(list(zip(gdf_webmerc.geometry.x.values, gdf_webmerc.geometry.y.values))))
        x0, y0 = points.min(axis=0)
        x1, y1 = points.max(axis=0)

        x0 = max(int(x0) - TRIM_MARGIN_PX, 0)
        y0 = max(int(y0) - TRIM_MARGIN_PX, 0)
        x1 = min(int(x1) + TRIM_MARGIN_PX, img.width)
        y1 = min(int(y1) + TRIM_MARGIN_PX, img.height)

        img_cropped = img.crop((x0, y0, x1, y1))
        img_cropped.save(output_crop)
        print(f"  [i] Immagine ritagliata salvata: {output_crop}")
    else:
        os.rename(output_full, output_crop)

    plt.close()
    print(f"  [+] Salvata: {output_crop}")
