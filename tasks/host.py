from django.utils import timezone
import datetime
import logging
import os
from ..models import Status, Host
from . import sh, telnet, log

logger = logging.getLogger(__name__)


def check_and_update(host: Host) -> None:
    """Check/update host and logs, monitord main function"""

    now = timezone.now()
    host.last_check = now

    # Only update changed fields in DB
    update_fields = ["last_check"]
    old_status_info = host.status_info

    sh.ping(host)
    if host.status == Status.SUCCESS:
        telnet.telnet_monitored_ports(host)

    # Update log only if retries reach max_retires
    if host.status == Status.DANGER and host.retries < host.max_retries:
        host.retries += 1
        update_fields.extend(["retries"])
        logger.warning(f"{host} {host.retries}/{host.max_retries} retry")

    else:
        # Reset retries if back online
        if host.status == Status.SUCCESS:
            if host.retries != 0:
                host.retries = 0
                update_fields.extend(["retries"])

        # Update status and logs if status info changed
        if old_status_info != host.status_info:
            msg = f'{host} changed from "{old_status_info}" to "{host.status_info}"'
            logger.info(msg)
            host.last_status_change = now
            update_fields.extend(["last_status_change", "status", "status_info"])
            log.update_hostlog(host)

        # Change the status from danger to warning if offline for days
        elif host.status == Status.DANGER:
            days_to_warning = os.getenv("DAYS_FROM_DANGER_TO_WARNING", 5)
            delta_to_warning_status = now - datetime.timedelta(days=days_to_warning)

            if host.last_status_change < delta_to_warning_status:
                host.status = Status.WARNING
                update_fields.extend(["status"])

    # Save only if the host was not deleted while in buffer
    host.save(update_fields=update_fields)
