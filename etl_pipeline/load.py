import pandas as pd
import os


STATIONS_FILE = './etl_pipeline/data/processed/station_points.parquet'
CONNECTORS_FILE = './etl_pipeline/data/processed/connectors.parquet'


def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(STATIONS_FILE) or not os.path.exists(CONNECTORS_FILE):
        return None, None
    
    stations_df = pd.read_parquet(STATIONS_FILE)
    connectors_df = pd.read_parquet(CONNECTORS_FILE)

    return stations_df, connectors_df


def save_processed_data(stations_df: pd.DataFrame, connectors_df: pd.DataFrame):
    stations_df.to_parquet(STATIONS_FILE, index=False)
    connectors_df.to_parquet(CONNECTORS_FILE, index=False)
