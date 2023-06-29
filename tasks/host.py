from django.utils import timezone
import datetime
import logging
import os
from ..models import Status, Host
from . import sh, telnet, log

logger = logging.getLogger(__name__)


def check_and_update(host: Host) -> None:
    """Monitord main function, check/update host and logs"""

    old_status_info = host.status_info
    now = timezone.now()
    host.last_check = now

    # Fields that will be updated on database
    update_fields = ["last_check"]

    sh.ping(host)
    if host.status == Status.SUCCESS:
        telnet.telnet_monitored_ports(host)

    # Reset retries if host is back online
    if host.status == Status.SUCCESS:
        if host.retries != 0:
            host.retries = 0
            update_fields.extend(["retries"])

    else:
        # Update status only if is offline and exceeded max_retries
        if host.retries < host.max_retries:
            host.retries += 1
            update_fields.extend(["retries"])
            msg = f"{host} {host.retries}/{host.max_retries} retry"
            logger.warning(msg)

        days_to_warning = os.getenv("DAYS_FROM_DANGER_TO_WARNING", 5)
        day_to_change_to_warning = now - datetime.timedelta(days=days_to_warning)

        # Update status to warning if is offline for x days
        if host.last_status_change > day_to_change_to_warning:
            host.status = Status.WARNING
            update_fields.extend(["status"])

    # Update info and create hostlog
    if host.status_info != old_status_info:
        msg = f"{host} info changed from {old_status_info} to {host.status_info}"
        logger.debug(msg)
        log.update_hostlog(host)
        update_fields.extend(["status_info"])

        # Don't update last_status_change for warning status
        if host.status != Status.WARNING:
            host.last_status_change = now
            update_fields.extend(["status", "last_status_change"])

    host.save(update_fields=update_fields)
