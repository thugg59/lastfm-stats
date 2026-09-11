import json
import os

import pytest
import requests

# extract.py validates these env vars at import time and calls
# SystemExit(1) if any are missing, so they must be set before import.
os.environ.setdefault("LASTFM_API_KEY", "test_api_key")
os.environ.setdefault("LASTFM_API_SECRET", "test_api_secret")
os.environ.setdefault("LASTFM_USERNAME", "test_user")
os.environ.setdefault("LASTFM_SESSION_KEY", "test_session_key")

from src import extract


def make_response(json_data, status_ok=True):
    class FakeResponse:
        def __init__(self, data, ok):
            self._data = data
            self._ok = ok

        def raise_for_status(self):
            if not self._ok:
                raise requests.HTTPError("HTTP error")

        def json(self):
            return self._data

    return FakeResponse(json_data, status_ok)


def make_track(name="Videotape", uts="1704110400"):
    return {
        "artist": {"#text": "Radiohead"},
        "album": {"#text": "In Rainbows"},
        "name": name,
        "date": {"uts": uts},
    }


@pytest.fixture(autouse=True)
def redirect_output(tmp_path, monkeypatch):
    scrobbles_json = tmp_path / "scrobbles.json"
    monkeypatch.setattr(extract, "SCROBBLES_JSON", scrobbles_json)
    return scrobbles_json


def test_default_mode_fetches_single_page_only(monkeypatch, redirect_output):
    calls = []

    def fake_get(url, params):
        calls.append(params)
        return make_response({
            "recenttracks": {
                "track": [make_track()],
                "@attr": {"totalPages": "5"},
            }
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=None, full_history=False)

    assert len(calls) == 1

    saved = json.loads(redirect_output.read_text())
    assert len(saved["recenttracks"]["track"]) == 1


def test_full_history_paginates_until_exhausted(monkeypatch, redirect_output):
    calls = []

    def fake_get(url, params):
        calls.append(params)
        page = params["page"]
        return make_response({
            "recenttracks": {
                "track": [make_track(name=f"Track{page}")],
                "@attr": {"totalPages": "3"},
            }
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=None, full_history=True)

    assert len(calls) == 3
    assert [c["page"] for c in calls] == [1, 2, 3]

    saved = json.loads(redirect_output.read_text())
    assert len(saved["recenttracks"]["track"]) == 3


def test_since_is_included_in_request_params(monkeypatch, redirect_output):
    calls = []

    def fake_get(url, params):
        calls.append(params)
        return make_response({
            "recenttracks": {"track": [], "@attr": {"totalPages": "1"}}
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=1700000000, full_history=False)

    assert calls[0]["from"] == 1700000000


def test_since_without_full_history_still_paginates(monkeypatch, redirect_output):
    # since is not None, so the "newest page only" break should not trigger,
    # even though full_history is False.
    calls = []

    def fake_get(url, params):
        calls.append(params)
        page = params["page"]
        return make_response({
            "recenttracks": {
                "track": [make_track(name=f"Track{page}")],
                "@attr": {"totalPages": "2"},
            }
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=1700000000, full_history=False)

    assert len(calls) == 2


def test_api_error_in_response_body_raises_system_exit(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response({"error": 6, "message": "Invalid parameters"})

    monkeypatch.setattr(extract.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        extract.fetch_scrobbles(since=None, full_history=False)

    assert exc_info.value.code == 1


def test_missing_recenttracks_key_raises_system_exit(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response({"unexpected": "shape"})

    monkeypatch.setattr(extract.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        extract.fetch_scrobbles(since=None, full_history=False)

    assert exc_info.value.code == 1


def test_network_failure_raises_system_exit(monkeypatch, redirect_output):
    def fake_get(url, params):
        raise requests.ConnectionError("network is down")

    monkeypatch.setattr(extract.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        extract.fetch_scrobbles(since=None, full_history=False)

    assert exc_info.value.code == 1


def test_http_error_status_raises_system_exit(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response(
            {"recenttracks": {"track": []}},
            status_ok=False,
        )

    monkeypatch.setattr(extract.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        extract.fetch_scrobbles(since=None, full_history=False)

    assert exc_info.value.code == 1


def test_single_track_dict_is_wrapped_in_list(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response({
            "recenttracks": {
                "track": make_track(),  # dict, not list
                "@attr": {"totalPages": "1"},
            }
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=None, full_history=False)

    saved = json.loads(redirect_output.read_text())
    assert len(saved["recenttracks"]["track"]) == 1


def test_missing_track_key_defaults_to_empty_list(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response({
            "recenttracks": {"@attr": {"totalPages": "1"}}
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=None, full_history=False)

    saved = json.loads(redirect_output.read_text())
    assert saved["recenttracks"]["track"] == []


def test_output_json_structure(monkeypatch, redirect_output):
    def fake_get(url, params):
        return make_response({
            "recenttracks": {
                "track": [make_track(name="Idioteque")],
                "@attr": {"totalPages": "1"},
            }
        })

    monkeypatch.setattr(extract.requests, "get", fake_get)

    extract.fetch_scrobbles(since=None, full_history=False)

    saved = json.loads(redirect_output.read_text())

    assert saved == {
        "recenttracks": {
            "track": [
                {
                    "artist": {"#text": "Radiohead"},
                    "album": {"#text": "In Rainbows"},
                    "name": "Idioteque",
                    "date": {"uts": "1704110400"},
                }
            ]
        }
    }