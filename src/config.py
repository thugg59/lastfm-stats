import logging
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
QUARANTINE_DIR = DATA_DIR / "quarantine"
LOG_DIR = DATA_DIR / "logs"

SCROBBLES_JSON = RAW_DIR / "scrobbles.json"
SCROBBLES_CSV = PROCESSED_DIR / "scrobbles.csv"
VALIDATED_CSV = PROCESSED_DIR / "validated_scrobbles.csv"
REJECTED_CSV = QUARANTINE_DIR / "rejected_scrobbles.csv"



def setup_logging(level=logging.INFO):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "pipeline.log"),
        ],
    )