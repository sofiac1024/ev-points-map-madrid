from collections import Counter
 
import numpy as np
import pandas as pd
from pyproj import Transformer
from sklearn.neighbors import BallTree


# Mean Earth radius, used to convert BallTree's haversine output (radians)
# into meters. A sphere approximation is more than accurate enough at
# city scale — the error versus the true ellipsoid is a few meters at
# most over distances of a few kilometers.
_EARTH_RADIUS_METERS = 6371000
 
# Beyond this distance, treat the "closest" OCM point as unrelated rather
# than force a match — protects data quality when the API has no real
# coverage for a given CSV point.
DEFAULT_MAX_MATCH_DISTANCE_METERS = 500.0

# Configure Transformer: from EPSG:25830 (UTM Madrid) to 
# EPSG:4326 (lat/lon WGS84) (model used by streamlit)
transformer = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)


def _build_ocm_spatial_index(api_points: list[dict]) -> tuple[BallTree | None, list[dict]]:
    """Build a haversine BallTree index over the OCM points' coordinates.
 
    Points missing a usable ``AddressInfo.Latitude``/``Longitude`` are
    dropped, since they can't be indexed or matched against anyway.
 
    Args:
        api_points: Raw POI list from ``extract.fetch_ocm_points``.
 
    Returns:
        tuple[BallTree | None, list[dict]]: The index (``None`` if there
        were no usable points) and the list of POI records it indexes,
        in the same order as the tree's internal point order — needed to
        map query result indices back to the original records.
    """
    # First get the API points we can get their coordinates from and use on the BallTree
    valid_points = [
        p
        for p in api_points
        if p.get("AddressInfo", {}).get("Latitude") is not None
        and p.get("AddressInfo", {}).get("Longitude") is not None
    ]
    if not valid_points:
        return None, []

    # Pass the points' coordinates into radians
    coords_rad = np.radians(
        [[p["AddressInfo"]["Latitude"], p["AddressInfo"]["Longitude"]] for p in valid_points]
    )
    tree = BallTree(coords_rad, metric="haversine")
    return tree, valid_points


def normalize_stations_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    # Rename column names
    df = raw_df.rename(columns={"UBICACIÓN": "location", 
                            "BARRIO": "neighborhood",
                            "OPERADOR": "operator",
                            "HORARIO": "timetable",
                            "GESTIÓN": "management"}).copy()

    # Normalize coordinates to later be used
    # Python only understands decimals with a point '.', not a comma ','

    # Vectorized string replace + cast: one pass over each column, not
    # one Python function call per row.
    coor_x = df.pop("POINT_X").str.replace(",", ".", regex=False).astype(float)
    coor_y = df.pop("POINT_Y").str.replace(",", ".", regex=False).astype(float)
 
    # Transformer.transform accepts arrays and returns arrays in one call.
    lon, lat = transformer.transform(coor_x.to_numpy(), coor_y.to_numpy())
    df["lon"] = lon
    df["lat"] = lat

    # Insert an ID column to connect with the connectors' DataFrame
    df.insert(0, "station_id", df.index)

    return df


def match_stations_to_ocm(
    station_coords: np.ndarray,
    api_points: list[dict],
    max_distance_meters: float = DEFAULT_MAX_MATCH_DISTANCE_METERS,
) -> list[dict | None]:
    tree, valid_points = _build_ocm_spatial_index(api_points)
    if tree is None:
        return [None] * len(station_coords)
 
    coords_rad = np.radians(station_coords)
    distances_rad, indices = tree.query(coords_rad, k=1)
    distances_meters = distances_rad[:, 0] * _EARTH_RADIUS_METERS
 
    matches = []
    for dist_m, idx in zip(distances_meters, indices[:, 0]):
        if dist_m > max_distance_meters:
            matches.append(None)
        else:
            matches.append(valid_points[idx])
 
    return matches
 
 
def build_station_and_connector_tables(
    stations_df: pd.DataFrame, api_points: list[dict]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    station_coords = stations_df[["lat", "lon"]].to_numpy()
    matches = match_stations_to_ocm(station_coords, api_points)
 
    usage_costs = []
    statuses = []
    connectors = []
 
    for station_id, match in zip(stations_df["station_id"], matches):
        usage_costs.append(match.get("UsageCost", "No info") if match else "No info")
        statuses.append(
            match.get("StatusType", {}).get("Title", "Unknown") if match else "Unknown"
        )
 
        if match:
            counts = Counter()
            power = {}
            for connection in match.get("Connections", []):
                title = connection["ConnectionType"]["Title"]
                counts[title] += 1
                power[title] = connection["PowerKW"]
 
            for connector_type, count in counts.items():
                connectors.append(
                    {
                        "station_id": station_id,
                        "connector_type": connector_type,
                        "power_kw": power.get(connector_type),
                        "count": count,
                    }
                )
 
    stations_df = stations_df.copy()
    stations_df["usage_cost"] = usage_costs
    stations_df["status"] = statuses
 
    connectors_df = pd.DataFrame(connectors)
    return stations_df, connectors_df
