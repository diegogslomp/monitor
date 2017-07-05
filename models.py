from django.db import models
from django.db.utils import DatabaseError
from django.utils import timezone
from .config.base import USER, PASSWORD
from .config.base import DAYS_FROM_DANGER_TO_WARNING, MAX_LOG_LINES
import datetime
import subprocess
import telnetlib
import re

class HostManager(models.Manager):
    def create_host(self, name, description, ipv4):
        return self.create(name=name, description=description, ipv4=ipv4)

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
                if host_ports.count() > 0:
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


    def status_handler(self):
        now = timezone.now()
        # if already whithout connection in 5 (default) or more days, 'warning' status
        status_tmp, status_info_tmp = self.telnet()

        if status_tmp == self.DANGER and self.status in (self.DANGER, self.WARNING) and \
                self.last_status_change <= (now - datetime.timedelta(days=DAYS_FROM_DANGER_TO_WARNING)):
           status_tmp = self.WARNING

        # Update host if status changed
        if self.status != status_tmp or self.status_info != status_info_tmp:
            self.status = status_tmp
            self.status_info = status_info_tmp
            # Don't change last updated time for warning changes
            if status_tmp != self.WARNING:
                self.last_status_change = now
                # Add new log
                Log.objects.create(host=self, status=status_tmp,
                                   status_info=status_info_tmp, status_change=now)
                # Remove old logs based on MAX_LOG_LINES
                Log.objects.filter(pk__in=Log.objects.filter(host=self).order_by('-status_change')
                                   .values_list('pk')[MAX_LOG_LINES:]).delete()
        # If the host still in the db, save it
        try:
            # Update only time and status fields
            self.save(update_fields=['last_check', 'last_status_change', 'status', 'status_info'])
        except DatabaseError as err:
            pass


    def __str__(self):
        return self.name

class LogManager(models.Manager):
    def create_log(self, host, status, status_change, status_info):
        return self.create(host=host, status=status, status_change=status_change,
                          status_info=status_info)


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
       return self.create(host=host, number=number)


class Port(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    objects = PortManager()

    def __str__(self):
        return self.number
