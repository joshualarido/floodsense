import ee
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")

def init_gee():
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)

def get_jrc_perm_water(lat: float, lon: float) -> dict:
    """
    Returns whether a point is classified as permanent water (JRC).
    Output:
        {
            "jrc_perm_water": 0 or 1
        }
    """
    point = ee.Geometry.Point([lon, lat])

    image = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

    value = image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("occurrence")

    # If occurrence is null → treat as 0
    occurrence = ee.Number(
        ee.Algorithms.If(value, value, 0)
    )

    perm_water = occurrence.gte(90)

    return {
        "jrc_perm_water": perm_water.getInfo()
    }

def get_precip_1d_3d(lat: float, lon: float, center_date: str) -> dict:
    """
    Returns precipitation totals (mm) for:
    - last 1 day
    - last 3 days
    using CHIRPS DAILY with latency- and emptiness-safe logic.
    """
    point = ee.Geometry.Point([lon, lat])

    # Safe latency offset for CHIRPS
    safe_end = ee.Date(center_date).advance(-3, "day")

    collection = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterBounds(point)
        .select("precipitation")
    )

    def compute_precip(days):
        col = collection.filterDate(
            safe_end.advance(-days, "day"), safe_end
        )

        size = col.size()

        def compute():
            img = col.sum()
            val = img.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=5000,
                maxPixels=1e9
            ).get("precipitation")
            return ee.Number(val)

        return ee.Number(
            ee.Algorithms.If(size.gt(0), compute(), 0)
        )

    precip_1d = compute_precip(1)
    precip_3d = compute_precip(3)

    return {
        "precip_1d": precip_1d.getInfo(),
        "precip_3d": precip_3d.getInfo()
    }

def _mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    mask = (
        qa.bitwiseAnd(cloud_bit).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit).eq(0))
    )

    return image.updateMask(mask).divide(10000)


def get_ndvi_ndwi(
    lat: float,
    lon: float,
    center_date: str,
    window_days: int = 15
) -> dict:
    point = ee.Geometry.Point([lon, lat])

    start = ee.Date(center_date).advance(-window_days, "day")
    end = ee.Date(center_date).advance(window_days, "day")

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(point)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .map(_mask_s2_clouds)
    )

    def add_indices(img):
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndwi = img.normalizedDifference(["B3", "B8"]).rename("NDWI")
        return img.addBands([ndvi, ndwi])

    collection = collection.map(add_indices)

    # 🚨 Check if collection is empty
    size = collection.size()

    def compute():
        image = collection.select(["NDVI", "NDWI"]).mean()

        stats = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point.buffer(100),
            scale=10,
            maxPixels=1e9
        )

        ndvi = ee.Number(stats.get("NDVI"))
        ndwi = ee.Number(stats.get("NDWI"))

        return ee.Dictionary({
            "NDVI": ndvi,
            "NDWI": ndwi
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
        "NDWI": result.get("NDWI").getInfo()
    }

def get_landcover(lat: float, lon: float) -> dict:
    """
    Returns ESA WorldCover landcover class at a point.
    Output:
        {
            "landcover": int
        }
    """
    point = ee.Geometry.Point([lon, lat])

    image = (
        ee.ImageCollection("ESA/WorldCover/v200")
        .first()
        .select("Map")
    )

    value = image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=10,
        maxPixels=1e9
    ).get("Map")

    landcover = ee.Number(
        ee.Algorithms.If(value, value, 0)
    )

    return {
        "landcover": landcover.getInfo()
    }

def get_dem_features(lat: float, lon: float) -> dict:
    """
    Returns elevation (m), slope (deg), and aspect (deg)
    from SRTM DEM.
    """
    point = ee.Geometry.Point([lon, lat])

    dem = ee.Image("USGS/SRTMGL1_003")

    terrain = ee.Terrain.products(dem)

    elevation = dem.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("elevation")

    slope = terrain.select("slope").reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("slope")

    aspect = terrain.select("aspect").reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("aspect")

    elevation = ee.Number(ee.Algorithms.If(elevation, elevation, 0))
    slope = ee.Number(ee.Algorithms.If(slope, slope, 0))
    aspect = ee.Number(ee.Algorithms.If(aspect, aspect, 0))

    return {
        "elevation": elevation.getInfo(),
        "slope": slope.getInfo(),
        "aspect": aspect.getInfo()
    }

def get_upstream_twi(lat: float, lon: float) -> dict:
    """
    Returns upstream contributing area (km²) and TWI,
    aligned with CSV flood-feature conventions.
    """
    point = ee.Geometry.Point([lon, lat])

    # HydroSHEDS flow accumulation (cell count)
    acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1")

    # DEM
    dem = ee.Image("USGS/SRTMGL1_003")

    # Slope (radians)
    slope_deg = ee.Terrain.slope(dem)
    slope_rad = slope_deg.multiply(3.141592653589793 / 180)

    # Pixel area in SAME projection as HydroSHEDS
    cell_area_m2 = ee.Image.pixelArea().reproject(acc.projection())

    # Upstream area in m²
    upstream_area_m2_img = acc.multiply(cell_area_m2)

    upstream_area_m2 = upstream_area_m2_img.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=acc.projection().nominalScale(),
        maxPixels=1e9
    ).get("b1")

    # Convert to km² (CSV-style)
    upstream_area_km2 = ee.Number(
        ee.Algorithms.If(upstream_area_m2, upstream_area_m2, 0)
    ).divide(1_000_000)

    # Slope at point
    slope = slope_rad.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30,
        maxPixels=1e9
    ).get("slope")

    slope = ee.Number(ee.Algorithms.If(slope, slope, 0.001))  # avoid tan(0)

    # TWI = ln(A / tan(beta)), A in km²
    twi = upstream_area_km2.divide(slope.tan()).log()

    return {
        "upstream_area": upstream_area_km2.getInfo(),
        "TWI": twi.getInfo()
    }

def build_features(lat: float, lon: float, date: str) -> dict:
    """
    Builds a model-ready feature payload.
    Output schema:
    {
        "features": [ ... ]  # ordered feature array
    }
    """

    # Collect features as dicts
    f = {}

    f.update(get_jrc_perm_water(lat, lon))
    f.update(get_precip_1d_3d(lat, lon, date))
    f.update(get_ndvi_ndwi(lat, lon, date))
    f.update(get_landcover(lat, lon))
    f.update(get_dem_features(lat, lon))
    f.update(get_upstream_twi(lat, lon))

    # IMPORTANT: order must match training CSV
    feature_array = [
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

    return {
        "features": feature_array
    }

