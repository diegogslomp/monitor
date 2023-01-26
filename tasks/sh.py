import logging
import subprocess
from ..models import Status
import os

logger = logging.getLogger(__name__)


def ping(host) -> None:
    """Ping host via shell and update status"""
    is_up = not subprocess.call(
        f"ping -4 -c3 -w1 -W5 {host.ipv4} | grep ttl= >/dev/null 2>&1",
        shell=True,
    )
    if is_up:
        host.status = Status.SUCCESS
        host.status_info = "Up"
    else:
        host.status = Status.DANGER
        host.status_info = "Down"
    logger.debug(f"{host.ipv4} - {host.name}: {host.status_info}")


def send_telegram_message(message: str) -> None:
    """Send Telegram via curl API"""

    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        message = "Telegram: Empty TELEGRAM_TOKEN and TELEGRAM_CHAT_ID"
        logger.warning(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    logger.info(f"Telegram: {message}")

    subprocess.call(
        f'curl -s -X POST {url} -d chat_id={chat_id} -d text="{message}" >/dev/null',
        shell=True,
    )
