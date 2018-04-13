from django.db import models
from django.utils import timezone
from .config.base import USER, PASSWORD, TELNET_TIMEOUT
from .config.base import DAYS_FROM_DANGER_TO_WARNING, MAX_LOG_LINES
import datetime
import logging
import re
import subprocess
import telnetlib


class Host(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
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
    logger = logging.getLogger(__name__)
    telnet_output = ''

    def __str__(self):
        return self.name

    @property
    def ports(self):
        return Port.objects.filter(host=self)

    @property
    def isalive(self):
        return not subprocess.call('ping {} -c 1 -W 2 -q > /dev/null 2>&1'\
                                    .format(self.ipv4), shell=True)

    def filter_telnet_output(self):
        '''Filter telnet output lines'''
        for line in self.telnet_output.lower().replace('\r', '').split('\n'):
            if re.search(r'[no ,in]valid', line):
                self.status = self.DANGER
                self.status_info = 'Invalid port registered or module is Down'
                self.logger.warning('{:14} {}'.format(self.ipv4, self.status_info.lower()))
                continue
            for port in self.ports:
                if re.search(r'{}.*down'.format(port.number), line):
                    self.status = self.DANGER
                    msg = 'Port {} ({}) is Down'.format(port.number, line.split()[1])
                    if self.status_info == 'Connected':
                        self.status_info = msg
                    else:
                        self.status_info += ', {}'.format(msg)
                    self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))

    def telnet(self):
        '''Telnet connection and get registered ports status'''
        self.logger.info('{:14} telnet started'.format(self.ipv4))
        try:
            tn = telnetlib.Telnet(self.ipv4, timeout=TELNET_TIMEOUT)
            tn.read_until(b"Username:", timeout=TELNET_TIMEOUT)
            tn.write(USER.encode('ascii') + b"\n")
            tn.read_until(b"Password:", timeout=TELNET_TIMEOUT)
            tn.write(PASSWORD.encode('ascii') + b"\n")
            # '->' for successful login or 'Username' for wrong credentials
            match_object = tn.expect([b"->", b"Username:"], timeout=TELNET_TIMEOUT)[1]
            if match_object.group(0) == b"Username:":
                self.status = self.DANGER
                self.status_info = 'Invalid telnet user or password'
                self.logger.warning('{:14} {}'.format(self.ipv4, self.status_info.lower()))
            else:
                for port in self.ports:
                    tn_command = 'show port status {0}'.format(port.number)
                    self.logger.info('{:14} {}'.format(self.ipv4, tn_command))
                    tn.write(tn_command.encode('ascii') + b"\n")
                tn.write(b"exit\n")
                self.logger.info('{:14} telnet finished'.format(self.ipv4))
                self.telnet_output = tn.read_all().decode('ascii')
                self.filter_telnet_output()
        except Exception as ex:
            self.status = self.DANGER
            self.status_info = 'Telnet error: {0}'.format(ex)
            self.logger.warning('{:14} {}'.format(self.ipv4, self.status_info.lower()))

    def check_connection(self):
        '''Ping host, then telnet if there are registered ports'''
        if self.isalive:
            self.status = self.SUCCESS
            self.status_info = 'Connected'
            self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))
            if self.ports.count() > 0:
                self.logger.info('{:14} telnet for registered ports'.format(self.ipv4))
                self.telnet()
        else:
            self.status = self.DANGER
            self.status_info = 'Connection Lost'
            self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))

    def update_logs(self):
        '''Add new log and remove old logs based on MAX_LOG_LINES'''
        try:
            Log.objects.create(host=self, status=self.status,
                               status_info=self.status_info, status_change=self.last_status_change)
            Log.objects.filter(pk__in=Log.objects.filter(host=self).order_by('-status_change')
                               .values_list('pk')[MAX_LOG_LINES:]).delete()
        except Exception as ex:
            self.logger.warning('{:14} db saving error: {}, perhaps was deleted from database'.format(self.ipv4, ex))


    def update_status(self):
        '''The 'main' function of monitord, check/update host and logs'''
        now = timezone.now()
        self.last_check = now
        # Only update changed fields in DB
        update_fields = ['last_check']
        # Store old data before change it
        old_status_info = self.status_info
        old_status = self.status
        self.check_connection()
        #  if status info changed, update status and logs
        if old_status_info != self.status_info:
            self.logger.info('{:14} status info changed from "{}" to "{}"'
                              .format(self.ipv4, self.status_info.lower(), old_status_info.lower()))
            self.last_status_change = now
            update_fields.extend(['last_status_change', 'status', 'status_info'])
            self.update_logs()
        # check if change the status from danger to warning status
        elif self.status == self.DANGER:
            delta_limit_to_warning_status = now - datetime.timedelta(days=DAYS_FROM_DANGER_TO_WARNING)
            if self.last_status_change <= delta_limit_to_warning_status:
                self.status = self.WARNING
                update_fields.extend(['status'])
        # Save only if the host was not deleted while in buffer
        try:
            self.save(update_fields=update_fields)
        except Exception as ex:
            self.logger.warning('{:14} db saving error: {}, perhaps was deleted from database'.format(self.ipv4, ex))


class Log(models.Model):
    '''Logs showed in host detail view'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return self.host.name


class Port(models.Model):
    '''Ports used to check status using telnet'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)

    def __str__(self):
        return self.number
