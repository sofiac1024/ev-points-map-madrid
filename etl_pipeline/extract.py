import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    retry_if_exception,
)


RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
API_URL = "https://api.openchargemap.io/v3/poi/"


def read_dataCSV(datafile_path: str) -> list[dict]:
    csv_df = pd.read_csv(datafile_path, delimiter=";")
    return csv_df


def _is_retryable_exception(exception: BaseException) -> bool:
    if isinstance(exception, requests.exceptions.HTTPError):
        return exception.response is not None and exception.response.status_code in RETRYABLE_STATUS_CODES
    
    return isinstance(exception, requests.exceptions.RequestException)

@retry(
    stop=stop_after_attempt(4), # Number of retries to request the API info
    # A backoff of waiting time following an exponential distribution with some 'jitter' 
    # (random volatility up to X seconds).
    wait=wait_exponential_jitter(initial=1, max=60, jitter=2), 
    # Conditions to retry:
    # 1. There must have been a Connection Error                OR
    # 2. The status code of the response must be a server error (5XX) or any other not 
    # related to our request (408, 425, 429)
    retry=(
        retry_if_exception_type(requests.exceptions.RequestException)
        | retry_if_exception(_is_retryable_exception)
    ),
    reraise=True,
)
def read_dataAPI(
        api_key: str,
        center_latitude: float = 40.4168,
        center_longitude: float = -3.7038,
        radius_distance: int = 100,
        max_results: int = 2500
) -> list[dict]:
    params = {
        "key": api_key,
        "latitude": center_latitude,   # Madrid center
        "longitude": center_longitude,  # Madrid center
        "distance": radius_distance,       
        "distanceunit": "KM",
        "maxresults": max_results,
        "usagetypeid": [1, 4] # Public or public with membership charging points
    }
    resp = requests.get(API_URL, params=params)
    ocm_data = resp.json()
    return ocm_data
