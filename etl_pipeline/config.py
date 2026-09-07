"""Configuration utilities for the EV charging points app.

This module centralizes access to sensitive configuration values (such as
the OpenChargeMap API key) so that no secret is ever hard-coded in the
source files. It supports two sources, checked in this order:

    1. Streamlit secrets (``st.secrets``), used when the app is deployed
       on Streamlit Community Cloud.
    2. A local ``.env`` file (loaded via ``python-dotenv``), used during
       local development.

Neither the ``.env`` file nor any real API key should ever be committed
to version control. See ``.gitignore`` in this project.
"""

import os

import streamlit as st
from dotenv import load_dotenv

# Load variables from a local .env file, if present. This is a no-op
# when the file does not exist (e.g. in the deployed environment).
load_dotenv()


def get_api_key() -> str:
    """Retrieve the OpenChargeMap API key from the available sources.

    The lookup order is:
        1. ``st.secrets["API_KEY"]`` (Streamlit Cloud deployment).
        2. The ``API_KEY`` environment variable (local development,
           typically defined in a ``.env`` file).

    Returns:
        str: The API key to authenticate against the OpenChargeMap API.

    Raises:
        RuntimeError: If no API key is found in either source.
    """
    api_key = None

    # st.secrets raises if no secrets.toml exists at all, so we guard it.
    try:
        api_key = st.secrets.get("API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv("API_KEY")

    if not api_key:
        raise RuntimeError(
            "API_KEY not found. Define it in a local '.env' file "
            "(API_KEY=your_key_here) or, for Streamlit Cloud, in the "
            "app's Secrets settings."
        )

    return api_key