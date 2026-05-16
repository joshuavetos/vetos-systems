"""
Geospatial Discovery Engine
Precision-biased SAR structural anomaly filter.

Fail-closed architecture:
A candidate must pass ALL gates to survive.

Tier 1: Localized Z-score screening (GRD)
Tier 2: Temporal stability validation (SLC coherence)
Tier 3: Morphology & topology validation
"""

import importlib
import importlib.util
import json

import numpy as np

# ---------------------------------------------------------------------
# CONFIGURATION (Peer-review explicit)
# ---------------------------------------------------------------------

PROJECT_ID = "project-c6f7bebe-f8b5-440e-994"

Z_THRESHOLD = 2.5
COHERENCE_FLOOR = 0.4
ORTHO_THRESHOLD = 0.15
ENTROPY_THRESHOLD = 2.5
FRACTAL_THRESHOLD = 1.4
MIN_PIXEL_SPAN = 15  # 150m @ 10m resolution

# ---------------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------------


def _require_module(module_name):
    root_module = module_name.split(".", 1)[0]
    if importlib.util.find_spec(root_module) is None:
        raise ImportError(
            f"{module_name} is required for this geospatial operation but is not installed"
        )
    if importlib.util.find_spec(module_name) is None:
        raise ImportError(
            f"{module_name} is required for this geospatial operation but is not installed"
        )
    return importlib.import_module(module_name)


def _require_earth_engine():
    return _require_module("ee")


def _require_skimage_tools():
    morphology = _require_module("skimage.morphology")
    measure = _require_module("skimage.measure")
    return morphology.skeletonize, measure.label, measure.regionprops


def initialize_ee():
    ee = _require_earth_engine()
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
    return ee


# ---------------------------------------------------------------------
# TIER 1: LOCALIZED Z-SCORE (GRD)
# ---------------------------------------------------------------------


def build_gate_result(name, verdict, lat, lon, **metrics):
    result = {
        "name": name,
        "coordinates": {"lat": float(lat), "lon": float(lon)},
        "verdict": verdict,
    }
    result.update(metrics)
    return result


def compute_local_z(image, point, buffer_dist=500):
    ee = _require_earth_engine()
    ambient = point.buffer(buffer_dist).difference(point.buffer(100))
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=ambient,
        scale=10,
        maxPixels=1e9,
    )
    mu = ee.Number(stats.get("VV_mean"))
    sigma = ee.Number(stats.get("VV_stdDev"))
    return image.subtract(mu).divide(sigma)


# ---------------------------------------------------------------------
# TIER 2: TEMPORAL STABILITY (SLC COHERENCE)
# ---------------------------------------------------------------------


def validate_mean_coherence(mean_coherence):
    if mean_coherence is None:
        return False

    try:
        value = float(mean_coherence)
    except (TypeError, ValueError):
        return False

    if not np.isfinite(value):
        return False

    return value >= COHERENCE_FLOOR


def compute_mean_coherence(coherence_image, geometry, scale=20, band_name="coherence"):
    """Compute mean coherence from a prepared Earth Engine coherence image.

    Returns ``None`` when Earth Engine reduction fails, the requested band is
    missing, or the reduced value is not finite. Discovery callers treat ``None``
    as fail-closed instead of allowing external EE runtime failures to crash a
    run.
    """
    try:
        ee = _require_earth_engine()
        stats = coherence_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9,
        )
        if stats is None:
            return None
        band_value = stats.get(band_name)
        if band_value is None:
            return None
        value = band_value.getInfo()
    except Exception:
        return None
    if value is None:
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric_value):
        return None
    return numeric_value


# ---------------------------------------------------------------------
# TIER 3: MORPHOLOGY GATE
# ---------------------------------------------------------------------


def box_count_fractal_dimension(binary):
    binary = np.asarray(binary, dtype=bool)
    min_side = min(binary.shape)
    sizes = [size for size in (2, 4, 8, 16) if size <= min_side]

    counts = []
    valid_sizes = []
    for size in sizes:
        rows = binary.shape[0] - (binary.shape[0] % size)
        cols = binary.shape[1] - (binary.shape[1] % size)
        if rows == 0 or cols == 0:
            continue

        cropped = binary[:rows, :cols]
        reduced = cropped.reshape((rows // size, size, cols // size, size)).max(axis=(1, 3))
        count = int(np.sum(reduced > 0))
        if count > 0:
            valid_sizes.append(size)
            counts.append(count)

    if len(counts) < 2:
        return 0.0

    coeffs = np.polyfit(np.log(valid_sizes), np.log(counts), 1)
    return float(-coeffs[0])


def compute_entropy(angles):
    angles = np.asarray(angles, dtype=float)
    if angles.size == 0:
        return 0.0

    hist, _ = np.histogram(angles % 180, bins=18, range=(0, 180), density=False)
    total = hist.sum()
    if total == 0:
        return 0.0

    probabilities = hist[hist > 0] / total
    return float(-np.sum(probabilities * np.log(probabilities)))


def skeleton_orientations(skeleton):
    points = np.argwhere(skeleton)
    if len(points) < 2:
        return np.array([], dtype=float)

    orientations = []
    point_set = {tuple(point) for point in points}
    for row, col in points:
        for d_row, d_col in ((0, 1), (1, 0), (1, 1), (1, -1)):
            if (row + d_row, col + d_col) in point_set:
                orientations.append(np.degrees(np.arctan2(d_row, d_col)) % 180)

    return np.array(orientations, dtype=float)


def analyze_structure(data):
    skeletonize, label, regionprops = _require_skimage_tools()
    binary = (data > np.percentile(data, 95)).astype(np.uint8)
    skeleton = skeletonize(binary > 0)

    labeled = label(skeleton)
    regions = regionprops(labeled)

    if not regions:
        return None

    largest = max(regions, key=lambda r: r.area)

    if largest.area < MIN_PIXEL_SPAN:
        return None

    eccentricity = largest.eccentricity
    fractal_dim = box_count_fractal_dimension(binary)
    entropy = compute_entropy(skeleton_orientations(skeleton))

    return {
        "length_pixels": largest.area,
        "eccentricity": float(eccentricity),
        "fractal_dimension": float(fractal_dim),
        "entropy": float(entropy),
    }


# ---------------------------------------------------------------------
# ENGINE ENTRYPOINT
# ---------------------------------------------------------------------


def run_discovery(name, lat, lon, mean_coherence=None):
    ee = initialize_ee()

    point = ee.Geometry.Point([lon, lat])
    buffer = point.buffer(500).bounds()

    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(buffer)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .sort("system:time_start", False)
        .first()
        .select("VV")
    )

    z_img = compute_local_z(s1, point)

    rect = z_img.sampleRectangle(region=buffer, defaultValue=0)
    data = np.array(rect.get("VV").getInfo())

    z_max = float(np.max(data))

    if z_max < Z_THRESHOLD:
        return build_gate_result(name, "FAIL_STATISTICAL", lat, lon, z_max=z_max)

    if not validate_mean_coherence(mean_coherence):
        return build_gate_result(name, "FAIL_COHERENCE", lat, lon, z_max=z_max)

    structure = analyze_structure(data)

    if structure is None:
        return build_gate_result(name, "FAIL_RESOLUTION", lat, lon)

    if structure["eccentricity"] > 0.92:
        return build_gate_result(name, "FAIL_LINEARITY", lat, lon, **structure)

    if structure["fractal_dimension"] > FRACTAL_THRESHOLD:
        return build_gate_result(name, "FAIL_FRACTAL", lat, lon, **structure)

    if structure["entropy"] > ENTROPY_THRESHOLD:
        return build_gate_result(name, "FAIL_ENTROPY", lat, lon, **structure)

    return build_gate_result(
        name,
        "STRUCTURAL_CANDIDATE",
        lat,
        lon,
        z_max=z_max,
        mean_coherence=float(mean_coherence),
        **structure,
    )


# ---------------------------------------------------------------------
# JSON PACKAGE OUTPUT
# ---------------------------------------------------------------------


def export_candidate_package(result, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
