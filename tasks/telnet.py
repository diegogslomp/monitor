import logging
from ..models import Port, Status
from django.utils import timezone
import re
import datetime
import os
import telnetlib
from . import log

logger = logging.getLogger(__name__)


def telnet_monitored_ports(host) -> None:
    """Filter telnet manually added monitored ports"""
    # Only check ports if online and has ports to be monitored
    if host.monitored_ports.count() <= 0:
        return

    ports = ";".join([port.number for port in host.monitored_ports])
    show_port_status = f"show port status {ports}"
    telnet_output = telnet(host, show_port_status)
    if not telnet_output:
        host.status = Status.DANGER
        host.status_info = "Can't get port status"
        logger.warning(host.status_info)
        return

    for line in telnet_output:
        if re.search(r"[no ,in]valid", line):
            host.status = Status.DANGER
            host.status_info = "Invalid port registered or module is Down"
            logger.warning(host.status_info)
            continue
        for port in host.monitored_ports:
            if re.search(r"{} .*down".format(port.number), line):
                host.status = Status.DANGER
                alias = line.split()[1]
                msg = f"Port {port.number} ({alias}) is Down"
                if host.status_info == "Up":
                    host.status_info = msg
                else:
                    host.status_info += f", {msg}"
                logger.debug(host.status_info)


def telnet_port_counters(host) -> None:
    """Filter telnet port counters, create ports and change status"""
    now = timezone.now()
    port_object = None
    telnet_output = telnet(host, "show port counters")

    if not telnet_output:
        return

    for line in telnet_output:
        # Create port if not exists
        if re.search(r"^port:", line):
            port_number = line.split()[1]
            logger.debug(f"Telnet filtered port: {port_number}")
            port_object = Port.objects.get_or_create(host=host, number=port_number)[0]
        elif re.search(r"^port :", line):
            port_number = line.split()[2]
            logger.debug(f"Telnet filtered port: {port_number}")
            port_object = Port.objects.get_or_create(host=host, number=port_number)[0]
        # Update counter and status
        elif re.search(r"^in errors", line):
            error_counter = int(line.split()[2])
            logger.debug(f"Telnet filtered counter: {error_counter}")
            logger.debug(f"Telnet old counter: {port_object.error_counter}")
            # Only save updated fields
            update_fields = []
            # If counter updated, change var and status
            if error_counter != port_object.error_counter:
                port_object.error_counter = error_counter
                port_object.counter_last_change = now
                port_object.counter_status = Status.DANGER
                update_fields.extend(
                    [
                        "error_counter",
                        "counter_last_change",
                        "counter_status",
                    ]
                )
                # Add port log if counter changed
                log.update_portlog(port_object)
                logger.debug(f"Telnet counter updated to: {error_counter}")
            else:
                old_counter_status = port_object.counter_status
                delta_1_day = now - datetime.timedelta(days=1)
                if port_object.counter_last_change <= delta_1_day:
                    port_object.counter_status = Status.WARNING
                delta_5_days = now - datetime.timedelta(days=5)
                if port_object.counter_last_change <= delta_5_days:
                    port_object.counter_status = Status.SUCCESS
                if old_counter_status != port_object.counter_status:
                    update_fields.extend(["counter_status"])
            if len(update_fields) > 0:
                try:
                    port_object.save(update_fields=update_fields)
                    logger.debug("Save port log to database")
                except Exception as e:
                    logger.warning(e)
            port_object = None


def telnet_gateway(host) -> str:
    """Filter gateway from telnet output"""

    telnet_output = telnet(host, "show ip route")
    if not telnet_output:
        return

    for line in telnet_output:
        if re.search(r"0.0.0.0", line):
            logger.debug(f"Telnet gateway line: {line}")
            if re.search("^\s*s", line):
                position = 4
            else:
                position = 1
            gateway = line.split()[position]
            logger.debug(f"Telnet gateway: {gateway}")
            return gateway


def telnet_switch_manager(host) -> None:
    """Get switch manager number"""

    telnet_output = telnet(host, "show switch")
    if not telnet_output:
        return

    for line in telnet_output:
        if re.search(r"[M,m]gmt", line):
            logger.debug(f"Telnet switch manager line: {line}")
            host.switch_manager = int(line.split()[0])
            logger.debug(f"Telnet switch manager: {host.switch_manager}")
            host.save(update_fields=["switch_manager"])
            return


def telnet(host, command: str) -> list[str]:
    """Telnet connection and get registered ports status"""
    telnet_output = []
    try:
        assert host.status == Status.SUCCESS

        timeout = os.getenv("TELNET_TIMEOUT", 5)
        user = os.getenv("TELNET_USER", "admin")
        password = os.getenv("TELNET_PASSWORD", "")

        with telnetlib.Telnet(host.ipv4, timeout=timeout) as tn:
            logger.debug("Telnet connection started")
            tn.read_until(b"Username:", timeout=timeout)
            tn.write(user.encode("ascii") + b"\n")
            tn.read_until(b"Password:", timeout=timeout)
            tn.write(password.encode("ascii") + b"\n")

            # '->' for successful login or 'Username' for wrong credentials
            matched_object = tn.expect([b"->", b"Username:"], timeout=timeout)
            if not matched_object[1]:
                raise ValueError("Telnet empty expect return")

            expected_match = matched_object[1].group(0)
            logger.debug(f"Telnet match: {expected_match}")
            if expected_match == b"Username:":
                raise PermissionError("Telnet invalid credentials")

            logger.debug(f"Telnet command: {command}")
            tn.write(command.encode("ascii") + b"\n")
            tn.write(b"exit\n")
            logger.debug("Telnet connection finished")

            telnet_output = (
                tn.read_all().decode("ascii").lower().replace("\r", "").split("\n")
            )
    except Exception as e:
        logger.warning(e)
    finally:
        return telnet_output
