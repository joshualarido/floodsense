import ee
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")

# =========================
# GEE INIT
# =========================
def init_gee():
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)

# =========================
# STATIC CONFIG
# =========================
STATIC_NDVI_DATE = "2023-08-15"  # Indonesia-safe Sentinel-2 date

# =========================
# JRC PERMANENT WATER
# =========================
def get_jrc_perm_water(lat: float, lon: float) -> dict:
    point = ee.Geometry.Point([lon, lat])

    image = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

    value = image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("occurrence")

    occurrence = ee.Number(ee.Algorithms.If(value, value, 0))
    perm_water = occurrence.gte(90)

    return {"jrc_perm_water": perm_water.getInfo()}

# =========================
# OPEN-METEO PRECIP
# =========================
def get_precip_1d_3d(lat: float, lon: float) -> dict:
    """
    Uses Open-Meteo daily precipitation_sum (mm).
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=3)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "timezone": "Asia/Singapore",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()

    daily = data.get("daily", {})
    precip = daily.get("precipitation_sum", [])

    # Defensive defaults
    precip = precip if precip else [0, 0, 0]

    precip_1d = precip[-1]
    precip_3d = sum(precip)

    return {
        "precip_1d": precip_1d,
        "precip_3d": precip_3d,
    }

# =========================
# SENTINEL-2 NDVI / NDWI (STATIC)
# =========================
def _mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    mask = (
        qa.bitwiseAnd(cloud_bit).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit).eq(0))
    )

    return image.updateMask(mask).divide(10000)

def get_ndvi_ndwi(lat: float, lon: float) -> dict:
    """
    NDVI / NDWI using a STATIC SAFE DATE (not real-time).
    """
    point = ee.Geometry.Point([lon, lat])

    center = ee.Date(STATIC_NDVI_DATE)
    start = center.advance(-15, "day")
    end = center.advance(15, "day")

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(point)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .map(_mask_s2_clouds)
    )

    def add_indices(img):
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndwi = img.normalizedDifference(["B3", "B8"]).rename("NDWI")
        return img.addBands([ndvi, ndwi])

    collection = collection.map(add_indices)

    size = collection.size()

    def compute():
        image = collection.select(["NDVI", "NDWI"]).median()

        stats = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point.buffer(100),
            scale=10,
            maxPixels=1e9
        )

        return ee.Dictionary({
            "NDVI": ee.Number(stats.get("NDVI")),
            "NDWI": ee.Number(stats.get("NDWI"))
        })

    result = ee.Dictionary(
        ee.Algorithms.If(
            size.gt(0),
            compute(),
            ee.Dictionary({"NDVI": 0, "NDWI": 0})
        )
    )

    return {
        "NDVI": result.get("NDVI").getInfo(),
        "NDWI": result.get("NDWI").getInfo(),
    }

# =========================
# LANDCOVER
# =========================
def get_landcover(lat: float, lon: float) -> dict:
    point = ee.Geometry.Point([lon, lat])

    image = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")

    value = image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=10,
        maxPixels=1e9
    ).get("Map")

    landcover = ee.Number(ee.Algorithms.If(value, value, 0))
    return {"landcover": landcover.getInfo()}

# =========================
# DEM FEATURES
# =========================
def get_dem_features(lat: float, lon: float) -> dict:
    point = ee.Geometry.Point([lon, lat])

    dem = ee.Image("USGS/SRTMGL1_003")
    terrain = ee.Terrain.products(dem)

    def safe(val):
        return ee.Number(ee.Algorithms.If(val, val, 0))

    elevation = safe(dem.reduceRegion(
        ee.Reducer.first(), point, 30, maxPixels=1e9
    ).get("elevation"))

    slope = safe(terrain.select("slope").reduceRegion(
        ee.Reducer.first(), point, 30, maxPixels=1e9
    ).get("slope"))

    aspect = safe(terrain.select("aspect").reduceRegion(
        ee.Reducer.first(), point, 30, maxPixels=1e9
    ).get("aspect"))

    return {
        "elevation": elevation.getInfo(),
        "slope": slope.getInfo(),
        "aspect": aspect.getInfo(),
    }

# =========================
# UPSTREAM AREA & TWI
# =========================
def get_upstream_twi(lat: float, lon: float) -> dict:
    point = ee.Geometry.Point([lon, lat])

    acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1")
    dem = ee.Image("USGS/SRTMGL1_003")

    # Pixel area aligned with HydroSHEDS
    cell_area = ee.Image.pixelArea().reproject(acc.projection())

    # Upstream area (m²)
    upstream_m2 = acc.multiply(cell_area).reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=acc.projection().nominalScale(),
        maxPixels=1e9
    ).get("b1")

    upstream_km2 = ee.Number(
        ee.Algorithms.If(upstream_m2, upstream_m2, 0)
    ).divide(1_000_000)

    # ---- SLOPE AS NUMBER (THIS IS THE KEY FIX) ----
    slope_deg = ee.Terrain.slope(dem).reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("slope")

    slope_rad = ee.Number(
        ee.Algorithms.If(slope_deg, slope_deg, 0.001)
    ).multiply(3.141592653589793 / 180)

    # Avoid tan(0)
    slope_rad = slope_rad.max(0.001)

    # TWI = ln(A / tan(beta))
    twi = upstream_km2.divide(slope_rad.tan()).log()

    return {
        "upstream_area": upstream_km2.getInfo(),
        "TWI": twi.getInfo(),
    }

# =========================
# BUILD FEATURES
# =========================
def build_features(lat: float, lon: float) -> dict:
    f = {}

    f.update(get_jrc_perm_water(lat, lon))
    f.update(get_precip_1d_3d(lat, lon))
    f.update(get_ndvi_ndwi(lat, lon))
    f.update(get_landcover(lat, lon))
    f.update(get_dem_features(lat, lon))
    f.update(get_upstream_twi(lat, lon))

    return {
        "features": [
            f["jrc_perm_water"],
            f["precip_1d"],
            f["precip_3d"],
            f["NDVI"],
            f["NDWI"],
            f["landcover"],
            f["elevation"],
            f["slope"],
            f["aspect"],
            f["upstream_area"],
            f["TWI"],
        ]
    }
