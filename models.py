from django.db import models
from django.db.utils import DatabaseError
from django.utils import timezone
from .config.base import USER, PASSWORD
from .config.base import DAYS_FROM_DANGER_TO_WARNING, MAX_LOG_LINES
import datetime
import subprocess
import telnetlib
import re


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


    @property
    def isalive(self):
        return  not subprocess.call('ping {0} -c 1 -W 2 -q > /dev/null 2>&1'\
                                    .format(self.ipv4), shell=True)

    def check_connection(self):
        '''Ping host, then telnet if there are registered ports'''

        output_status = self.DANGER
        output_info = 'Connection Lost'

        if self.isalive:
            output_status = self.SUCCESS
            output_info = 'Connected'
            host_ports = Port.objects.filter(host=self)
            if host_ports.count() > 0:
                tn = telnetlib.Telnet(self.ipv4)
                tn.read_until(b"Username:")
                tn.write(USER.encode('ascii') + b"\n")
                tn.read_until(b"Password:")
                tn.write(PASSWORD.encode('ascii') + b"\n")
                # Wait prompt '->' for successful login or 'Username' for wrong credentials
                match_object = tn.expect([b"->", b"Username:"])[1]
                if match_object.group(0) == b"Username:":
                    output_status = Host.DANGER
                    output_info = 'Invalid telnet user or password'
                else:
                    for port in host_ports:
                        tn_command = 'show port status {0}'.format(port.number)
                        tn.write(tn_command.encode('ascii') + b"\n")
                    tn.write(b"exit\n")
                    # Filter telnet output lines
                    for line in tn.read_all().decode('ascii').lower().replace('\r', '').split('\n'):
                        if re.search(r'[no ,in]valid', line):
                            output_status = self.DANGER
                            output_info = 'Invalid port registered or module is Down'
                            continue
                        for port in host_ports:
                            if re.search(r'{0}.*down'.format(port.number), line):
                                output_status = self.DANGER
                                msg = 'Port {0} ({1}) is Down'.format(port.number, line.split()[1])
                                if output_info == 'Connected':
                                    output_info = msg
                                else:
                                    output_info += ', {0}'.format(msg)

        return output_status, output_info


    def update_logs(self):
        '''Add new log and remove old logs based on MAX_LOG_LINES'''
        Log.objects.create(host=self, status=self.status,
                           status_info=self.status_info, status_change=self.last_status_change)
        Log.objects.filter(pk__in=Log.objects.filter(host=self).order_by('-status_change')
                           .values_list('pk')[MAX_LOG_LINES:]).delete()


    def update_status(self):
        '''The 'main' function of monitord, check/update host and logs'''
        now = timezone.now()
        self.last_check = now
        # Only update changed fields in DB
        updated_fields = ['last_check']
        status_tmp, status_info_tmp = self.check_connection()

        #  if status info changed, update status and logs
        if status_info_tmp != self.status_info:
            self.status = status_tmp
            self.status_info = status_info_tmp
            self.last_status_change = now
            updated_fields.extend(['last_status_change', 'status', 'status_info'])
            self.update_logs()

        # if only status changed, got from danger to warning
        elif status_tmp != self.status:

            delta_limit_to_warning_status = now - datetime.timedelta(days=DAYS_FROM_DANGER_TO_WARNING)
            # if already whithout connection in 5 (default) or more days, 'warning' status
            if status_tmp == self.DANGER and self.last_status_change <= delta_limit_to_warning_status:
                self.status = self.WARNING
                updated_fields.extend(['status'])

        # If the host still in the db, save it
        try:
            # Update only time and status fields
            self.save(update_fields=updated_fields)
        except DatabaseError as err:
            # TODO: Add logger to catch
            pass

    def __str__(self):
        return self.name


class Log(models.Model):
    '''Logs showed in host detail view'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.host.name


class Port(models.Model):
    '''Ports used to check status using telnet'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)

    def __str__(self):
        return self.number
