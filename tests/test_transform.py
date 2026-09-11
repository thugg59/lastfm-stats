from datetime import datetime, timezone

from src.transform import _clean_tracks


def make_track(artist="Radiohead", album="In Rainbows", name="Videotape", uts="1704110400"):
    return {
        "artist": {"#text": artist},
        "album": {"#text": album},
        "name": name,
        "date": {"uts": uts},
    }


def test_full_track_parses_correctly():
    tracks = [make_track()]

    cleaned = _clean_tracks(tracks)

    assert len(cleaned) == 1
    assert cleaned[0]["artist"] == "Radiohead"
    assert cleaned[0]["album"] == "In Rainbows"
    assert cleaned[0]["track"] == "Videotape"
    assert cleaned[0]["timestamp"] == datetime.fromtimestamp(1704110400, tz=timezone.utc)


def test_missing_album_key_defaults_to_none():
    track = make_track()
    del track["album"]

    cleaned = _clean_tracks([track])

    assert len(cleaned) == 1
    assert cleaned[0]["album"] is None


def test_album_present_but_missing_text_defaults_to_none():
    track = make_track()
    track["album"] = {}

    cleaned = _clean_tracks([track])

    assert len(cleaned) == 1
    assert cleaned[0]["album"] is None


def test_now_playing_track_is_skipped():
    track = make_track()
    track["@attr"] = {"nowplaying": "true"}

    cleaned = _clean_tracks([track])

    assert cleaned == []


def test_missing_artist_is_skipped():
    track = make_track()
    del track["artist"]

    cleaned = _clean_tracks([track])

    assert cleaned == []


def test_missing_name_is_skipped():
    track = make_track()
    del track["name"]

    cleaned = _clean_tracks([track])

    assert cleaned == []


def test_missing_date_is_skipped():
    track = make_track()
    del track["date"]

    cleaned = _clean_tracks([track])

    assert cleaned == []


def test_malformed_uts_is_skipped():
    track = make_track(uts="not-a-number")

    cleaned = _clean_tracks([track])

    assert cleaned == []


def test_single_track_dict_is_wrapped_in_list():
    track = make_track()

    cleaned = _clean_tracks(track)

    assert len(cleaned) == 1


def test_multiple_tracks_mixed_valid_and_invalid():
    good = make_track()
    bad = make_track()
    del bad["artist"]

    cleaned = _clean_tracks([good, bad])

    assert len(cleaned) == 1
    assert cleaned[0]["artist"] == "Radiohead"


def test_single_malformed_track_dict_is_skipped():
    track = make_track()
    del track["artist"]

    cleaned = _clean_tracks(track)

    assert cleaned == []