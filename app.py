"""Streamlit app: public EV charging points map for the city of Madrid.
 
This is the presentation layer only. It lays out the page (map tab and
statistics tab), wires up sidebar filters, and renders the Folium map and
Plotly charts. All data loading, API calls and data-shaping logic live in
"data_utils.py", and secret/config handling lives in "config.py".
 
Run locally with:
    streamlit run app.py
"""

import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import plotly.express as px
from keys import API_KEY
from data_utils import read_dataAPI, popup_html, download_stations_toCSV


station_points = read_dataAPI()
filtered_points = station_points.copy()


# Title of the webpage
st.header("Puntos de recarga públicos para vehículos eléctricos en Madrid (España)")

# Create tabs for specific functionalities
tab1, tab2 = st.tabs(['Mapa de Estaciones', 'Estadísticas'])

with tab1:
    # Create a dynamic map with Streamlit_Folium centered in MADRID
    MADRID_CENTRE = (40.41677473410711, -3.7037457319298768) # Format EPSG:4326 (lat/lon WGS84)
    # Crear mapa centrado en Madrid Centro
    map = folium.Map(location=MADRID_CENTRE, zoom_start=11.5)
    # Add pointers' clustering
    marker_cluster = plugins.MarkerCluster().add_to(map)

    # EXTRA PLUGINS
    # Add a location searcher: GeoCoder
    plugins.Geocoder(collapsed=True).add_to(map)
    # Add filters in a sidebar
    st.html('''
        <style>
        /* Restrict the max. height for all selected filtering options,
            including a scroll if necesary */
        div[data-testid="stMultiSelect"] [data-baseweb="select"] > div > div {
            max-height: 114px; 
            overflow: auto;
        }
            
        [data-testid="stSidebarHeader"] {
            height: 1.25rem; 
        }
        </style>
    ''')
    st.sidebar.header("Filtros")
    # Create a void div space in the sidebar (above the filters) to make a counter
    counter = st.sidebar.empty()

    # DISTRICT filter
    districs = sorted(station_points['neighborhood'].unique())
    selected_district = st.sidebar.multiselect("**Selecciona barrio(s):**", districs, placeholder="")
    # MANAGEMENT filter
    managements = sorted(station_points['management'].unique())
    selected_management = st.sidebar.multiselect("**Selecciona tipo(s) de gestión:**", managements, placeholder="")
    # OPERATOR filter
    operators = sorted(station_points['operator'].unique())
    selected_operator = st.sidebar.multiselect("**Selecciona operador(es):**", operators, placeholder="")
    # TYPE OF CONECTORS filter
    all_connectors = sorted({c for conns in station_points['connections'] for c in conns})  # set para evitar duplicados
    selected_connectors = st.sidebar.multiselect("**Selecciona tipo(s) de conector:**", all_connectors, placeholder="")
    # Apply filters
    if selected_district:
        filtered_points = filtered_points[filtered_points['neighborhood'].isin(selected_district)]
    if selected_operator:
        filtered_points = filtered_points[filtered_points['operator'].isin(selected_operator)]
    if selected_management:
        filtered_points = filtered_points[filtered_points['management'].isin(selected_management)]
    if selected_connectors:
        filtered_points = filtered_points[
        filtered_points['connections'].apply(lambda conns: any(conn in conns for conn in selected_connectors))
        ]
    # Count filtered charging points
    counter.metric(label="**Puntos de recarga coincidentes:**", value=len(filtered_points))
    
    
    csv_export = download_stations_toCSV(filtered_points)
    st.download_button(
        label="Exportar estaciones filtradas a CSV",
        data=csv_export,
        file_name="estaciones_filtradas.csv",
        mime="text/csv"
    )


    for _, point in filtered_points.iterrows():
        mark = point['lat'], point['lon']
        folium.Marker(
            mark,
            popup=popup_html(point),
            tooltip=point["location"],
            icon=folium.Icon(color='green', icon='bolt', icon_color='white', prefix='fa')  # ícono tipo "rayo" de FontAwesome (fa)
        ).add_to(marker_cluster)


    # Call to render the interactive map with Folium on the Streamlit site 
    st.header("Mapa Interactivo")
    st_data = st_folium(map, width=700, height=450)



with tab2:
    # Some statistics about the distribution and interesting 
    # caracteristics of the represented charging points
    st.header("Estadísticas Relevantes")
    # Group and count by neighborhood
    df_neighborhoods = (
        filtered_points.groupby("neighborhood")
        .size()
        .reset_index(name="count")
    )
    # Sort from highest to lowest and get the first 10 neighborhoods
    df_top10 = df_neighborhoods.sort_values("count", ascending=False).head(10)
    # Bar chart
    chart1 = px.bar(
        df_top10,
        x="neighborhood",
        y="count",
        title="Top 10 barrios con más puntos de recarga",
        color="count",
        text="count",
        labels={
            "neighborhood": "Barrio",   # rename X axis
            "count": "Número de puntos de recarga"  # rename Y axis
        }
    )
    # Sort the bars by count
    chart1.update_layout(xaxis={'categoryorder': 'total descending'})
    # PLot the graph
    st.plotly_chart(chart1, use_container_width=True)

    # Now we do the same but by most common operators of these charging points
    df_operators = filtered_points.groupby("operator").size().reset_index(name="count")
    chart2 = px.pie(
        df_operators,
        names="operator",      
        values="count",        
        title="Número de puntos de recarga por operador",
        hover_data=["count"], 
        labels={
            "operator": "Operador",   # rename X axis
            "count": "Número de puntos de recarga"  # rename Y axis
        } 
    )   
    st.plotly_chart(chart2, use_container_width=True)