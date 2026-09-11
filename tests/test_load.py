import os
from datetime import datetime, timezone

import pandas as pd
import psycopg
import pytest

# load.py validates these env vars at import time and calls
# SystemExit(1) if any are missing, so they must be set before import.
os.environ.setdefault("DB_HOST", "test_host")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from src import load


# ---------------------------------------------------------------------------
# Fake psycopg connection/cursor/copy objects
# ---------------------------------------------------------------------------

class FakeCopy:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def write_row(self, row):
        self.cursor.copied_rows.append(row)


class FakeCursor:
    def __init__(self, fetchone_result=None, rowcount=0, raise_on=None):
        self.executed = []
        self.copied_rows = []
        self._fetchone_result = fetchone_result
        self.rowcount = rowcount
        self._raise_on = raise_on or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        self.executed.append(sql)
        for marker, exc in self._raise_on.items():
            if marker in sql:
                raise exc

    def fetchone(self):
        return self._fetchone_result

    def copy(self, sql):
        return FakeCopy(self)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def cursor(self):
        return self._cursor


def make_fake_connect(cursor, raise_on_connect=None):
    def fake_connect(**kwargs):
        if raise_on_connect:
            raise raise_on_connect
        return FakeConnection(cursor)
    return fake_connect


# ---------------------------------------------------------------------------
# get_last_timestamp
# ---------------------------------------------------------------------------

def test_get_last_timestamp_returns_none_when_no_scrobbles(monkeypatch):
    cursor = FakeCursor(fetchone_result=(None,))
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    result = load.get_last_timestamp()

    assert result is None


def test_get_last_timestamp_returns_none_when_fetchone_returns_none(monkeypatch):
    cursor = FakeCursor(fetchone_result=None)
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    result = load.get_last_timestamp()

    assert result is None


def test_get_last_timestamp_returns_epoch_plus_one_second(monkeypatch):
    last = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    cursor = FakeCursor(fetchone_result=(last,))
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    result = load.get_last_timestamp()

    assert result == int(last.timestamp()) + 1


def test_get_last_timestamp_raises_system_exit_on_db_error(monkeypatch):
    monkeypatch.setattr(
        load.psycopg,
        "connect",
        make_fake_connect(FakeCursor(), raise_on_connect=psycopg.Error("connection failed")),
    )

    with pytest.raises(SystemExit) as exc_info:
        load.get_last_timestamp()

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# load_scrobbles
# ---------------------------------------------------------------------------

def make_validated_csv(tmp_path, rows):
    path = tmp_path / "validated_scrobbles.csv"
    columns = ["artist", "track", "album", "timestamp"]
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
    return path


def test_load_scrobbles_missing_input_file_raises_system_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(load, "VALIDATED_CSV", tmp_path / "does_not_exist.csv")

    with pytest.raises(SystemExit) as exc_info:
        load.load_scrobbles()

    assert exc_info.value.code == 1


def test_load_scrobbles_missing_required_columns_raises_system_exit(tmp_path, monkeypatch):
    path = tmp_path / "validated_scrobbles.csv"
    pd.DataFrame([{"artist": "Radiohead", "track": "Videotape"}]).to_csv(path, index=False)
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    with pytest.raises(SystemExit) as exc_info:
        load.load_scrobbles()

    assert exc_info.value.code == 1


def test_load_scrobbles_no_records_returns_without_connecting(tmp_path, monkeypatch):
    path = make_validated_csv(tmp_path, [])
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    connect_calls = []
    monkeypatch.setattr(
        load.psycopg,
        "connect",
        lambda **kwargs: connect_calls.append(kwargs) or FakeConnection(FakeCursor()),
    )

    load.load_scrobbles()

    assert connect_calls == []


def test_load_scrobbles_happy_path_copies_and_inserts(tmp_path, monkeypatch):
    path = make_validated_csv(tmp_path, [
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
        {"artist": "Radiohead", "track": "Idioteque", "album": "Kid A",
         "timestamp": "2024-01-02T12:00:00Z"},
    ])
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    cursor = FakeCursor(rowcount=2)
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    load.load_scrobbles()

    assert len(cursor.copied_rows) == 2
    assert cursor.copied_rows[0] == ("Radiohead", "Videotape", "In Rainbows", "2024-01-01T12:00:00Z")
    assert any("CREATE TEMP TABLE" in sql for sql in cursor.executed)
    assert any("INSERT INTO scrobbles" in sql for sql in cursor.executed)


def test_load_scrobbles_null_album_converted_to_none(tmp_path, monkeypatch):
    path = make_validated_csv(tmp_path, [
        {"artist": "Radiohead", "track": "Videotape", "album": None,
         "timestamp": "2024-01-01T12:00:00Z"},
    ])
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    cursor = FakeCursor(rowcount=1)
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    load.load_scrobbles()

    assert cursor.copied_rows[0][2] is None


def test_load_scrobbles_computes_inserted_and_skipped(tmp_path, monkeypatch, caplog):
    path = make_validated_csv(tmp_path, [
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
        {"artist": "Radiohead", "track": "Idioteque", "album": "Kid A",
         "timestamp": "2024-01-02T12:00:00Z"},
    ])
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    # Only 1 of the 2 records actually got inserted (the other was a duplicate).
    cursor = FakeCursor(rowcount=1)
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    with caplog.at_level("INFO"):
        load.load_scrobbles()

    assert "1 inserted, 1 duplicates skipped" in caplog.text


def test_load_scrobbles_db_error_raises_system_exit(tmp_path, monkeypatch):
    path = make_validated_csv(tmp_path, [
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
    ])
    monkeypatch.setattr(load, "VALIDATED_CSV", path)

    cursor = FakeCursor(raise_on={"INSERT INTO scrobbles": psycopg.Error("insert failed")})
    monkeypatch.setattr(load.psycopg, "connect", make_fake_connect(cursor))

    with pytest.raises(SystemExit) as exc_info:
        load.load_scrobbles()

    assert exc_info.value.code == 1