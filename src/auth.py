import os
import requests
import logging
from dotenv import load_dotenv, set_key
from pathlib import Path
from src.lastfm import sign_request


logger = logging.getLogger(__name__)
load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")

API_URL = "https://ws.audioscrobbler.com/2.0/"


def get_token():
    logger.info("Requesting Last.fm authentication token")

    params = {
        "method": "auth.getToken",
        "api_key": API_KEY,
        "format": "json"
    }

    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(
            f"Last.fm API error {data['error']}: "
            f"{data.get('message', 'Unknown error')}"
        )

    token = data["token"]

    print("\nOpen this URL in your browser:")
    print(
        f"https://www.last.fm/api/auth/?api_key={API_KEY}&token={token}"
    )

    return token


def save_session_key(session_key):
    env_path = Path(".env")
    env_path.touch(exist_ok=True)

    set_key(
        dotenv_path=env_path,
        key_to_set="LASTFM_SESSION_KEY",
        value_to_set=session_key,
    )

    logger.info("Session key saved to .env")


def get_session(token):
    logger.info("Requesting Last.fm session key")

    params = {
        "method": "auth.getSession",
        "api_key": API_KEY,
        "token": token,
        "format": "json"
    }

    api_sig = sign_request(params, API_SECRET)
    params["api_sig"] = api_sig

    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(
            f"Last.fm API error {data['error']}: "
            f"{data.get('message', 'Unknown error')}"
        )

    session_key = data["session"]["key"]

    save_session_key(session_key)


if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()
    token = get_token()

    input(
        "\nAfter authorizing the application, press ENTER to continue..."
    )

    get_session(token)