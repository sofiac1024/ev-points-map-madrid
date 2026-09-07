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

import pandas as pd
import streamlit as st


def popup_html(point: pd.Series, connectors_df: pd.DataFrame) -> str:
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
    connections = connectors_df.loc[connectors_df["station_id"] == point["station_id"]]
    if not connections.empty:
        rows = [
            f"<tr><td>{con.connector_type}</td><td>{con.power_kw} kW</td><td>{con.count}</td></tr>"
            for con in connections.itertuples()
        ]
        
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
    <b>Coste:</b> {point['usage_cost']}<br>
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