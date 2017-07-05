from django.db import models
from django.utils import timezone
from .config.base import USER, PASSWORD
from .config.base import DAYS_FROM_DANGER_TO_WARNING, WAIT_FOR_NEXT, MAX_LOG_LINES
import subprocess
import telnetlib
import re

class HostManager(models.Manager):
    def create_host(self, name, description, ipv4):
        host = self.create(name=name, description=description, ipv4=ipv4)
        return host

class Host(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    ipv4 = models.GenericIPAddressField(protocol='IPv4')
    last_check = models.DateTimeField('last check', default=timezone.now)
    last_status_change = models.DateTimeField('last status change', default=timezone.now)
    status_info = models.CharField(max_length=200, blank=True, default='')

    DEFAULT = 0
    SUCCESS = 1
    INFO = 2
    WARNING = 3
    DANGER = 4

    STATUS_CHOICES = (
        (DEFAULT, 'secondary'),
        (SUCCESS, 'positive'),
        (INFO, 'primary'),
        (WARNING, 'warning'),
        (DANGER, 'negative'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=DEFAULT)
    objects = HostManager()

    @property
    def isalive(self):
        return  not subprocess.call('ping {0} -c 1 -W 2 -q > /dev/null 2>&1'\
                                    .format(self.ipv4), shell=True)

    def telnet(self):
        if not self.isalive:
            telnet_status = self.DANGER
            telnet_info = 'Connection Lost'
        else:
            telnet_status = self.SUCCESS
            telnet_info = 'Connected'
            tn = telnetlib.Telnet(self.ipv4)
            tn.read_until(b"Username:")
            tn.write(USER.encode('ascii') + b"\n")
            tn.read_until(b"Password:")
            tn.write(PASSWORD.encode('ascii') + b"\n")
            # Wait prompt '->' for successful login or 'Username' for wrong credentials
            match_object = tn.expect([b"->", b"Username:"])[1]
            if match_object.group(0) == b"Username:":
                telnet_status = Host.DANGER
                telnet_info = 'Invalid telnet user or password'
            else:
                host_ports = Port.objects.filter(host=self)
                if host_ports.count() <= 0:
                    telnet_status = Host.DANGER
                    telnet_info = 'No registered port found'
                else:
                    for port in host_ports:
                        tn_command = 'show port status {0}'.format(port.number)
                        tn.write(tn_command.encode('ascii') + b"\n")
                    tn.write(b"exit\n")
                    # Filter telnet output lines
                    for line in tn.read_all().decode('ascii').lower().replace('\r', '').split('\n'):
                        if re.search(r'[no ,in]valid', line):
                            telnet_status = self.DANGER
                            telnet_info = 'Invalid port registered or module is Down'
                            continue
                        for port in host_ports:
                            if re.search(r'{0}.*down'.format(port.number), line):
                                telnet_status = self.DANGER
                                msg = 'Port {0} ({1}) is Down'.format(port.number, line.split()[1])
                                if telnet_info == 'Connected':
                                    telnet_info = msg
                                else:
                                    telnet_info += ', {0}'.format(msg)

        return telnet_status, telnet_info

    def __str__(self):
        return self.name

class LogManager(models.Manager):
    def create_log(self, host, status, status_change, status_info):
        log = self.create(host=host, status=status, status_change=status_change,
                          status_info=status_info)
        return log

class Log(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, null=True)
    objects = LogManager()

    def __str__(self):
        return self.host.name

class PortManager(models.Manager):
    def create_port(self, host, number):
        port = self.create(host=host, number=number)
        return port

class Port(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    objects = PortManager()

    def __str__(self):
        return self.number
