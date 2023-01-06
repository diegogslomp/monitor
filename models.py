from django.db import models
from django.utils import timezone
import datetime
import logging
import re
import subprocess
import telnetlib
import os


logger = logging.getLogger(__name__)


def send_telegram_message(host):
    """Send Telegram via curl API"""

    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        message = "Telegram: Empty TELEGRAM_TOKEN and TELEGRAM_CHAT_ID"
        logger.warning(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    icon = "\u2705" if host.status < host.WARNING else "\u274C"
    message = f"{icon} {host.name} - {host.status_info}"
    logger.info(f"Telegram: {message}")

    subprocess.call(
        f'curl -s -X POST {url} -d chat_id={chat_id} -d text="{message}" >/dev/null',
        shell=True,
    )


class Telnet:
    """Telnet methods"""

    @staticmethod
    def telnet_monitored_ports(host):
        """Filter telnet manually added monitored ports"""

        # Only check ports if online and has ports to be monitored
        if host.monitored_ports.count() <= 0:
            return

        try:
            ports = ";".join([port.number for port in host.monitored_ports])
            show_port_status = f"show port status {ports}"
            telnet_output = Telnet.telnet(host, show_port_status)
        except:
            host.status = host.DANGER
            host.status_info = "Telnet: Can't get port status"
            logger.warning(f"Telnet: {ex}")
            return

        for line in telnet_output:
            if re.search(r"[no ,in]valid", line):
                host.status = host.DANGER
                host.status_info = "Invalid port registered or module is Down"
                logger.warning(f"Telnet: {host.status_info}")
                continue
            for port in host.monitored_ports:
                if re.search(r"{} .*down".format(port.number), line):
                    host.status = host.DANGER
                    alias = line.split()[1]
                    msg = f"Port {port.number} ({alias}) is Down"
                    if host.status_info == "Up":
                        host.status_info = msg
                    else:
                        host.status_info += f", {msg}"
                    logger.debug(f"Telnet: {host.status_info}")

    @staticmethod
    def telnet_port_counters(host):
        """Filter telnet port counters, create ports and change status"""
        now = timezone.now()
        port_object = None
        try:
            telnet_output = Telnet.telnet(host, "show port counters")
        except Exception as ex:
            logger.warning(f"Telnet: {ex}")
            return

        for line in telnet_output:
            # Create port if not exists
            if re.search(r"^port:", line):
                port_number = line.split()[1]
                logger.debug(f"Telnet filtered port: {port_number}")
                port_object = Port.objects.get_or_create(
                    host=host, number=port_number
                )[0]
            elif re.search(r"^port :", line):
                port_number = line.split()[2]
                logger.debug(f"Telnet filtered port: {port_number}")
                port_object = Port.objects.get_or_create(
                    host=host, number=port_number
                )[0]
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
                    port_object.counter_status = Host.DANGER
                    update_fields.extend(
                        [
                            "error_counter",
                            "counter_last_change",
                            "counter_status",
                        ]
                    )
                    # Add port log if counter changed
                    port_object.update_log()
                    logger.debug(f"Telnet counter updated to: {error_counter}")
                else:
                    old_counter_status = port_object.counter_status
                    delta_1_day = now - datetime.timedelta(days=1)
                    if port_object.counter_last_change <= delta_1_day:
                        port_object.counter_status = host.WARNING
                    delta_5_days = now - datetime.timedelta(days=5)
                    if port_object.counter_last_change <= delta_5_days:
                        port_object.counter_status = host.SUCCESS
                    if old_counter_status != port_object.counter_status:
                        update_fields.extend(["counter_status"])
                if len(update_fields) > 0:
                    try:
                        port_object.save(update_fields=update_fields)
                        logger.debug("Save port log to database")
                    except Exception as ex:
                        logger.warning(ex)
                port_object = None

    @staticmethod
    def telnet_gateway(host):
        """Filter gateway from telnet output"""
        try:
            telnet_output = Telnet.telnet(host, "show ip route")
        except Exception as ex:
            logger.warning(f"Telnet: {ex}")
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

    @staticmethod
    def telnet_switch_manager(host):
        """Get switch manager number"""

        try:
            telnet_output = Telnet.telnet(host, "show switch")
        except Exception as ex:
            logger.warning(f"Telnet: {ex}")
            return

        for line in telnet_output:
            if re.search(r"[M,m]gmt", line):
                logger.debug(f"Telnet switch manager line: {line}")
                host.switch_manager = int(line.split()[0])
                logger.debug(f"Telnet switch manager: {host.switch_manager}")
                host.save(update_fields=["switch_manager"])
                return

    @staticmethod
    def telnet(host, command) -> list[str]:
        """Telnet connection and get registered ports status"""

        assert host.status == host.SUCCESS

        timeout = os.getenv("TELNET_TIMEOUT", 5)
        user = os.getenv("TELNET_USER", "admin")
        password = os.getenv("TELNET_PASSWORD", "")

        with telnetlib.Telnet(host.ipv4, timeout=timeout) as tn:
            logger.debug("Telnet: Connection started")
            tn.read_until(b"Username:", timeout=timeout)
            tn.write(user.encode("ascii") + b"\n")
            tn.read_until(b"Password:", timeout=timeout)
            tn.write(password.encode("ascii") + b"\n")

            # '->' for successful login or 'Username' for wrong credentials
            matched_object = tn.expect([b"->", b"Username:"], timeout=timeout)
            if not matched_object[1]:
                raise ValueError("Telnet: Empty expect return")

            expected_match = matched_object[1].group(0)
            logger.debug(f"Telnet match: {expected_match}")
            if expected_match == b"Username:":
                raise PermissionError("Telnet: Invalid credentials")

            logger.debug(f"Telnet command: {command}")
            tn.write(command.encode("ascii") + b"\n")
            tn.write(b"exit\n")
            logger.debug("Telnet: Connection finished")

            telnet_output = (
                tn.read_all().decode("ascii").lower().replace("\r", "").split("\n")
            )
            return telnet_output


class Host(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    ipv4 = models.GenericIPAddressField(protocol="IPv4")
    last_check = models.DateTimeField("last check", default=timezone.now)
    last_status_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    status_info = models.CharField(max_length=200, blank=True, default="")
    network = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    circuit = models.IntegerField(null=True, blank=True)
    retries = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=1)
    local = models.CharField(max_length=200, null=True, blank=True)
    switch_manager = models.IntegerField(null=True, blank=True, default=0)
    DEFAULT = 0
    SUCCESS = 1
    INFO = 2
    WARNING = 3
    DANGER = 4
    STATUS_CHOICES = (
        (DEFAULT, "secondary"),
        (SUCCESS, "positive"),
        (INFO, "primary"),
        (WARNING, "warning"),
        (DANGER, "negative"),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=DEFAULT)

    def __str__(self):
        return self.name

    @property
    def ports(self):
        return Port.objects.filter(host=self)

    @property
    def monitored_ports(self):
        return Port.objects.filter(host=self, is_monitored=True)

    def ping(self):
        """Ping host via shell and update status"""
        is_up = not subprocess.call(
            f"ping -4 -c3 -w1 -W5 {self.ipv4} | grep ttl= >/dev/null 2>&1",
            shell=True,
        )
        if is_up:
            self.status = self.SUCCESS
            self.status_info = "Up"
        else:
            self.status = self.DANGER
            self.status_info = "Down"
        logger.debug(f"Ping {self.ipv4} - {self.name}: {self.status_info}")

    def update_log(self):
        """Add new host log and remove old logs based on MAX_LOG_LINES"""
        try:
            max_log_lines = os.getenv("MAX_LOG_LINES", 20)
            HostLog.objects.create(
                host=self,
                status=self.status,
                status_info=self.status_info,
                status_change=self.last_status_change,
            )
            HostLog.objects.filter(
                pk__in=HostLog.objects.filter(host=self)
                .order_by("-status_change")
                .values_list("pk")[max_log_lines:]
            ).delete()
            send_telegram_message(self)
        except Exception as ex:
            logger.warning(f"HostLog: {ex}")

    def check_and_update(self):
        """The 'main' function of monitord, check/update host and logs"""
        now = timezone.now()
        self.last_check = now
        # Only update changed fields in DB
        update_fields = ["last_check"]
        # Store old data before change it
        old_status = self.status
        old_status_info = self.status_info
        self.ping()
        Telnet.telnet_monitored_ports(self)
        # Update log only if retries reach max_retires
        if self.status == self.DANGER and self.retries < self.max_retries:
            self.retries += 1
            update_fields.extend(["retries"])
            logger.warning(f"{self.ipv4}: {self.retries}/{self.max_retries} retry")
        else:
            # if online, reset retries
            if self.status == self.SUCCESS:
                self.retries = 0
                update_fields.extend(["retries"])
            # if status info changed, update status and logs
            if old_status_info != self.status_info:
                logger.debug(
                    f'{self.ipv4}: Status info changed from "{old_status_info}" to "{self.status_info}"'
                )
                self.last_status_change = now
                update_fields.extend(["last_status_change", "status", "status_info"])
                self.update_log()
            # check if change the status from danger to warning status
            elif self.status == self.DANGER:
                days_to_warning = os.getenv("DAYS_FROM_DANGER_TO_WARNING", 5)
                delta_limit_to_warning_status = now - datetime.timedelta(
                    days=days_to_warning
                )
                if self.last_status_change <= delta_limit_to_warning_status:
                    self.status = self.WARNING
                    update_fields.extend(["status"])
        # Save only if the host was not deleted while in buffer
        try:
            self.save(update_fields=update_fields)
        except Exception as ex:
            logger.warning(ex)


class HostLog(models.Model):
    """Host Logs showed in host detail view"""

    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return self.host.name


class Port(models.Model):
    """Ports used to check status using telnet"""

    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    is_monitored = models.BooleanField(default=False)
    counter_status = models.IntegerField(
        choices=Host.STATUS_CHOICES, default=Host.DEFAULT
    )
    counter_last_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    error_counter = models.BigIntegerField(default=0)

    def update_log(self):
        """Add new port log and remove old logs based on MAX_LOG_LINES"""
        try:
            max_log_lines = os.getenv("MAX_LOG_LINES", 20)
            PortLog.objects.create(
                port=self,
                host=self.host,
                counter_status=self.counter_status,
                counter_last_change=self.counter_last_change,
                error_counter=self.error_counter,
            )
            PortLog.objects.filter(
                pk__in=PortLog.objects.filter(port=self)
                .order_by("-counter_last_change")
                .values_list("pk")[max_log_lines:]
            ).delete()
        except Exception as ex:
            logger.warning(ex)

    def __str__(self):
        return self.number


class PortLog(models.Model):
    """Port Logs showed in host detail view"""

    port = models.ForeignKey(Port, on_delete=models.CASCADE, null=True)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True)
    counter_status = models.IntegerField(
        choices=Host.STATUS_CHOICES, default=Host.DEFAULT
    )
    counter_last_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    error_counter = models.IntegerField(default=0)

    def __str__(self):
        return self.port.number


class Dio(models.Model):
    """DIO Bastidor Optico"""

    pop = models.ForeignKey(Host, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Fibra(models.Model):
    """Portas/Fibras dos DIO"""

    dio = models.ForeignKey(Dio, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    port = models.CharField(max_length=20, blank=True, default="")
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.number
