from django.utils import timezone
import datetime
import logging
import os
from ..models import Status, Host
from . import sh, telnet, log

logger = logging.getLogger(__name__)


def check_and_update(host: Host) -> None:
    """The 'main' function of monitord, check/update host and logs"""
    now = timezone.now()
    host.last_check = now
    # Only update changed fields in DB
    update_fields = ["last_check"]
    # Store old data before change it
    old_status_info = host.status_info
    sh.ping(host)
    if host.status == Status.SUCCESS:
        telnet.telnet_monitored_ports(host)
    # Update log only if retries reach max_retires
    if host.status == Status.DANGER and host.retries < host.max_retries:
        host.retries += 1
        update_fields.extend(["retries"])
        logger.warning(f"{host.ipv4}: {host.retries}/{host.max_retries} retry")
    else:
        # if online, reset retries
        if host.status == Status.SUCCESS:
            host.retries = 0
            update_fields.extend(["retries"])
        # if status info changed, update status and logs
        if old_status_info != host.status_info:
            logger.debug(
                f'{host.ipv4}: Status info changed from "{old_status_info}" to "{host.status_info}"'
            )
            host.last_status_change = now
            update_fields.extend(["last_status_change", "status", "status_info"])
            log.update_hostlog(host)
        # check if change the status from danger to warning status
        elif host.status == Status.DANGER:
            days_to_warning = os.getenv("DAYS_FROM_DANGER_TO_WARNING", 5)
            delta_limit_to_warning_status = now - datetime.timedelta(
                days=days_to_warning
            )
            if host.last_status_change <= delta_limit_to_warning_status:
                host.status = Status.WARNING
                update_fields.extend(["status"])
    # Save only if the host was not deleted while in buffer
    host.save(update_fields=update_fields)
