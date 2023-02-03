import logging
import os
from ..models import HostLog, Status, PortLog, Host, Port
from . import sh

logger = logging.getLogger(__name__)


def update_hostlog(host: Host) -> None:
    """Add new host log and remove old logs based on MAX_LOG_LINES"""
    try:
        max_log_lines = os.getenv("MAX_LOG_LINES", 20)
        HostLog.objects.create(
            host=host,
            status=host.status,
            status_info=host.status_info,
            status_change=host.last_status_change,
        )
        HostLog.objects.filter(
            pk__in=HostLog.objects.filter(host=host)
            .order_by("-status_change")
            .values_list("pk")[max_log_lines:]
        ).delete()

        icon = "🟢" if host.status < Status.WARNING else "🔴"
        message = f"{icon} {host.name} - {host.status_info}"
        sh.send_telegram_message(message)

    except Exception as e:
        logger.warning(f"HostLog: {e}")


def update_portlog(port: Port) -> None:
    """Add new port log and remove old logs based on MAX_LOG_LINES"""
    try:
        max_log_lines = os.getenv("MAX_LOG_LINES", 20)
        PortLog.objects.create(
            port=port,
            host=port.host,
            counter_status=port.counter_status,
            counter_last_change=port.counter_last_change,
            error_counter=port.error_counter,
        )
        PortLog.objects.filter(
            pk__in=PortLog.objects.filter(port=port)
            .order_by("-counter_last_change")
            .values_list("pk")[max_log_lines:]
        ).delete()
    except Exception as e:
        logger.warning(e)
