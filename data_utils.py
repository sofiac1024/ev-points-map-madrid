"""Data loading and processing utilities for EV charging points in Madrid.
 
This module is responsible for everything that is not directly related to
rendering the Streamlit UI: reading the public CSV dataset, querying the
OpenChargeMap API, merging both data sources, and building small
presentation helpers (such as the HTML used inside map popups) that are
still considered "data shaping" rather than page layout.
 
Keeping this logic separate from ``app.py`` makes the project easier to
test, reuse, and reason about: the UI file only has to worry about layout
and widgets, while this file owns the data pipeline.
"""

import csv
import pandas as pd
import streamlit as st
from pyproj import Transformer
import requests, json
from geopy.distance import geodesic
from collections import Counter
from config import get_api_key


API_KEY = get_api_key()
API_URL = "https://api.openchargemap.io/v3/poi/"
DATA_FILE = 'PUNTOS_PUBLICOS_RECARGA_VEHICULOS_ELECTRICOS.csv'
# Configure Transformer: from EPSG:25830 (UTM Madrid) to 
# EPSG:4326 (lat/lon WGS84) (model used by streamlit)
transformer = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)

def find_ocm_match(datafile_point: dict, api_points: list[dict]):
    """Enrich a CSV charging point with data from its closest OCM match.
 
    Compares the point's coordinates against every point returned by the
    OpenChargeMap (OCM) API and finds the geographically closest one.
    The matched record's cost, connector, and status information is then
    copied into ``point`` in place.
 
    Args:
        point: A dictionary representing a single charging point parsed
            from the local CSV file. Must contain ``lat`` and ``lon``
            keys. Modified in place with the keys ``usageCost``,
            ``connections``, ``connectionsKW`` and ``status``.
        api_points: The list of POI records returned by the OpenChargeMap
            API (``response.json()``). If empty, the function returns
            without modifying ``point``.
 
    Returns:
        None. The ``point`` dictionary is updated in place.
    """
    if not api_points:
        return
    
    # Compare by distance between the "p" charging point from the CSV file to all the "api_points" from
    # the used API to find the closest match
    best_match = None
    min_dist = 1e9
    for r in api_points:
        r_lat = r["AddressInfo"]["Latitude"]
        r_lon = r["AddressInfo"]["Longitude"]
        dist = geodesic((datafile_point['lat'], datafile_point['lon']), (r_lat, r_lon)).meters
        if dist < min_dist:
            min_dist = dist
            best_match = r

    datafile_point["usageCost"] = best_match.get("UsageCost", "No info")
    cnt = Counter()
    power = dict()
    for c in best_match.get("Connections", []):
        cnt[c["ConnectionType"]["Title"]] += 1
        power[c["ConnectionType"]["Title"]] = c["PowerKW"]
    datafile_point["connections"] = cnt
    datafile_point["connectionsKW"] = power
    datafile_point["status"] = best_match.get("StatusType", {}).get("Title", "Desconocido")
    return


"""@st.cache_data: Saves the first DataFrame created and only updates 
    it if there has been changes in the input data or in the function 
"""
@st.cache_data 
def read_dataCSV() -> list[dict]:
    """Read and parse the local CSV of public EV charging points.
 
    The source file uses semicolon-separated values, comma decimal
    notation, and UTM (EPSG:25830) coordinates. This function normalizes
    all of that into a list of plain dictionaries with lat/lon in
    WGS84 (EPSG:4326), ready to be merged with the API data or plotted
    on a Folium map.
 
    Cached with ``st.cache_data`` so the file is parsed only once per
    session, unless the underlying data or function code changes.
 
    Returns:
        list[dict]: One dictionary per charging point, with keys
        ``location``, ``neighborhood``, ``operator``, ``timetable``,
        ``management``, ``lon`` and ``lat``.
    """
    points_data = []
    with open(DATA_FILE, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            # Python only understands decimals with a point '.', not a comma ','
            coorX = float(row['POINT_X'].replace(',', '.'))
            coorY = float(row['POINT_Y'].replace(',', '.'))
            # We transform the coordinates to the right format for streamlit to parse it correctly
            lon, lat = transformer.transform(coorX, coorY)
            points_data.append({
                'location' : row['UBICACIÓN'],
                'neighborhood' : row['BARRIO'],
                'operator' : row['OPERADOR'],
                'timetable' : row['HORARIO'],
                'management' : row['GESTIÓN'],
                'lon' : lon,
                'lat' : lat
            })
    return points_data


@st.cache_data
def read_dataAPI() -> pd.DataFrame:
    """Fetch OpenChargeMap data and merge it with the local CSV dataset.
 
    Queries the OpenChargeMap API for public charging points within a
    100 km radius of central Madrid, then enriches every point parsed
    from the local CSV (see :func:`read_data_csv`) with the closest
    matching API record via :func:`find_ocm_match`.
 
    Cached with ``st.cache_data`` so the (rate-limited) API is called
    only once per session.
 
    Returns:
        pd.DataFrame: One row per charging point, combining the fields
        from the CSV with the OCM-derived fields (``usageCost``,
        ``connections``, ``connectionsKW``, ``status``).
    """
    params = {
        "key": API_KEY,
        "latitude": 40.4168,   # Madrid center
        "longitude": -3.7038,  # Madrid center
        "distance": 100,       
        "distanceunit": "KM",
        "maxresults": 2000,
        "usagetypeid": [1, 4] # Public or public with membership charging points
    }
    resp = requests.get(API_URL, params=params)
    ocm_data = resp.json()
    # Parse the charging points from our csv file 
    csv_data = read_dataCSV()

    # Complement each charging point obtained in 'csv_data' with the info. got from its closest 
    # charging point from 'ocm_data'
    for p in csv_data:
        find_ocm_match(p, ocm_data)
    return pd.DataFrame(csv_data)


def popup_html(point: pd.Series) -> str:
    """Build the HTML content shown inside a charging point's map popup.
 
    Args:
        point: A row (``pd.Series``) from the charging points DataFrame,
            expected to contain the keys ``location``, ``neighborhood``,
            ``operator``, ``timetable``, ``usageCost``, ``connections``,
            ``connectionsKW`` and ``status``.
 
    Returns:
        str: An HTML snippet ready to be passed to
        ``folium.Marker(popup=...)``.
    """
    if isinstance(point["connections"], dict) and isinstance(point["connectionsKW"], dict):
        rows = []
        for ctype in point["connections"].keys():
            count = point["connections"].get(ctype, "N/A")
            kw = point["connectionsKW"].get(ctype, "N/A")
            rows.append(f"<tr><td>{ctype}</td><td>{kw} kW</td><td>{count}</td></tr>")
        
        connectors_str = f"""
        <table style="width:100%; font-size:11px; border-collapse:collapse;" border="1">
            <tr style="font-weight:bold; background-color:#f0f0f0;">
                <td>Tipo</td>
                <td>Potencia</td>
                <td>Cargadores</td>
            </tr>
            {''.join(rows)}
        </table>
        """
    else:
        connectors_str = "N/A"

    return f"""
    <div style="width: 250px; font-size: 12px;">
    <b>Ubicación:</b> {point['location']}<br>
    <b>Barrio:</b> {point['neighborhood']}<br>
    <b>Operador:</b> {point['operator']}<br>
    <b>Horario:</b> {point['timetable']}<br>
    <b>Coste:</b> {point['usageCost']}<br>
    <b>Conectores:</b><br>{connectors_str}<br>
    <b>Estado:</b> {point['status']}<br>
    """


# Option to export filtered charging points into a csv file
@st.cache_data
def download_stations_toCSV(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to UTF-8-encoded CSV bytes.
 
    Used to power the "download filtered results" button, since
    ``st.download_button`` requires raw bytes rather than a DataFrame.
 
    Args:
        dataframe: The (typically filtered) DataFrame to export.
 
    Returns:
        bytes: The CSV representation of ``dataframe``, UTF-8 encoded.
    """
    return df.to_csv(index=False).encode('utf-8')