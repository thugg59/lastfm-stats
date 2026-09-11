#!/usr/bin/env python3
"""Detect and select the PostgreSQL session timezone, writing DB_TIMEZONE to .env."""
import os
import re
from pathlib import Path
from zoneinfo import available_timezones

from dotenv import set_key

ENV_PATH = Path(".env")

# Shortlist shown by default; anything else is reachable via manual entry.
COMMON_TIMEZONES = [
    "Europe/Warsaw",
    "Europe/Berlin",
    "Europe/London",
    "Europe/Paris",
    "America/New_York",
    "America/Los_Angeles",
    "UTC",
]


def detect_timezone() -> str | None:
    """Best-effort detection via /etc/localtime (Linux/macOS only)."""
    localtime = Path("/etc/localtime")
    if not localtime.is_symlink():
        return None

    target = os.readlink(localtime)
    match = re.search(r"zoneinfo/(.+)$", target)
    if not match:
        return None

    zone = match.group(1)
    return zone if zone in available_timezones() else None


def prompt_selection(detected: str | None) -> str:
    options = list(COMMON_TIMEZONES)
    if detected and detected not in options:
        options.insert(0, detected)

    default_index = options.index(detected) + 1 if detected in options else 1

    if detected:
        print(f"Detected timezone: {detected}")
    else:
        print("Could not auto-detect timezone.")

    print("\nAvailable timezones:")
    for i, tz in enumerate(options, start=1):
        print(f"[{i}] {tz}")
    print("[m] Enter manually (any IANA zone, e.g. Asia/Tokyo)")

    choice = input(f"\nEnter number [{default_index}]: ").strip()

    if not choice:
        return options[default_index - 1]

    if choice.lower() == "m":
        manual = input("Enter IANA timezone name: ").strip()
        if manual not in available_timezones():
            raise SystemExit(f"Unknown timezone: {manual}")
        return manual

    if not choice.isdigit() or not (1 <= int(choice) <= len(options)):
        raise SystemExit(f"Invalid selection: {choice}")

    return options[int(choice) - 1]


def main():
    detected = detect_timezone()
    selected = prompt_selection(detected)

    ENV_PATH.touch(exist_ok=True)
    set_key(dotenv_path=ENV_PATH, key_to_set="DB_TIMEZONE", value_to_set=selected)

    print(f"\nSaved DB_TIMEZONE={selected} to .env")


if __name__ == "__main__":
    main()