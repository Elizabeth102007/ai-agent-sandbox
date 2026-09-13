
import logging
import os


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        filename="logs/travel_planner.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        encoding="utf-8"
    )

    # Keep HTTP library noise out of the log unless it's a warning/error.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger("travel_planner")