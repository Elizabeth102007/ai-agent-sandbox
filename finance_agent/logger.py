import logging
import os


def setup_logging() -> None:
    """Configures application-wide logging to a dedicated file in logs/."""
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        filename="logs/finance_agent.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        encoding="utf-8"
    )

    # Keep verbose HTTP/network noise out of the log file
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


logger = logging.getLogger("finance_agent")