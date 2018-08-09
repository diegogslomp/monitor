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

    def __str__(self):
        return self.name

    @property
    def ports(self):
        return Port.objects.filter(host=self)

    @property
    def monitored_ports(self):
        return Port.objects.filter(host=self, is_monitored=True)

    @property
    def isalive(self):
        return not subprocess.call('ping {} -c 1 -W 2 -q > /dev/null 2>&1'\
                                    .format(self.ipv4), shell=True)

    def check_monitored_ports_status(self):
        '''Filter telnet manually added monitored ports'''
        if self.monitored_ports.count() > 0:

            def telnet_commands_monitored_ports():
                commands = []
                for port in self.monitored_ports:
                    commands.append('show port status {0}'.format(port.number))
                return commands

            self.logger.info('{:14} telnet to check monitored ports'.format(self.ipv4))
            telnet_output = self.telnet(telnet_commands_monitored_ports())    
            if telnet_output != '':
                for line in telnet_output.lower().replace('\r', '').split('\n'):
                    if re.search(r'[no ,in]valid', line):
                        self.status = self.DANGER
                        self.status_info = 'Invalid port registered or module is Down'
                        self.logger.warning('{:14} {}'.format(self.ipv4, self.status_info.lower()))
                        continue
                    for port in self.monitored_ports:
                        if re.search(r'{}.*down'.format(port.number), line):
                            self.status = self.DANGER
                            msg = 'Port {} ({}) is Down'.format(port.number, line.split()[1])
                            if self.status_info == 'Connected':
                                self.status_info = msg
                            else:
                                self.status_info += ', {}'.format(msg)
                            self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))

    def check_port_counters(self):
        '''Filter telnet port counters, create ports and change status'''
        if self.isalive and not re.search(r'^RADIO', self.name):
            now = timezone.now()
            telnet_output = self.telnet(['show port counters'])
            if telnet_output != '':
                port_object = None
                for line in telnet_output.lower().replace('\r', '').split('\n'):
                    # Create port if not exists
                    if re.search(r'^port:', line):
                        port_number = line.split()[1]
                        self.logger.info('{:14} Filtered Port: {}'.format(self.ipv4, port_number))
                        port_object = Port.objects.get_or_create(host=self, number=port_number)[0]
                    elif re.search(r'^port :', line):
                        port_number = line.split()[2]
                        self.logger.info('{:14} Filtered Port: {}'.format(self.ipv4, port_number))
                        port_object = Port.objects.get_or_create(host=self, number=port_number)[0]
                    # Update counter and status
                    elif re.search(r'^in errors', line):
                        error_counter = int(line.split()[2])
                        self.logger.info('{:14} Filtered Counter: {}'.format(self.ipv4, error_counter))
                        self.logger.info('{:14} Old Counter: {}'.format(self.ipv4, port_object.error_counter))
                        # If conter updated, change var and status
                        if error_counter != port_object.error_counter:
                            port_object.error_counter = error_counter
                            port_object.counter_last_change = now
                            port_object.counter_status = Host.DANGER  
                            # Add port log if counter changed
                            port_object.update_log()  
                            self.logger.info('{:14} counter updated to: {}'.format(self.ipv4, error_counter))
                        else:
                            # TODO: Add update status logic
                            delta_1_day = now - datetime.timedelta(days=1)
                            if port_object.counter_last_change <= delta_1_day:
                                port_object.counter_status = self.WARNING
                            delta_5_days = now - datetime.timedelta(days=5)
                            if port_object.counter_last_change <= delta_5_days:
                                port_object.counter_status = self.SUCCESS
                            pass
                        try:
                            port_object.save()
                        except Exception as ex:
                            self.logger.warning('{:14} db saving error: {}, perhaps was deleted from database'.format(self.ipv4, ex))
                        port_object = None
                      
    def telnet(self, commands):
        '''Telnet connection and get registered ports status'''
        self.logger.info('{:14} telnet started'.format(self.ipv4))
        telnet_output = ''
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
                for tn_command in commands:
                    self.logger.info('{:14} {}'.format(self.ipv4, tn_command))
                    tn.write(tn_command.encode('ascii') + b"\n")
                tn.write(b"exit\n")
                self.logger.info('{:14} telnet finished'.format(self.ipv4))
                telnet_output = tn.read_all().decode('ascii')
        except Exception as ex:
            self.status = self.DANGER
            self.status_info = 'Telnet error: {0}'.format(ex)
            self.logger.warning('{:14} {}'.format(self.ipv4, self.status_info.lower()))
        finally:
            return telnet_output

    def check_ping(self):
        '''Ping host, then telnet if there are registered ports'''
        if self.isalive:
            self.status = self.SUCCESS
            self.status_info = 'Connected'
            self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))
        else:
            self.status = self.DANGER
            self.status_info = 'Connection Lost'
            self.logger.info('{:14} {}'.format(self.ipv4, self.status_info.lower()))

    def update_log(self):
        '''Add new host log and remove old logs based on MAX_LOG_LINES'''
        try:
            HostLog.objects.create(host=self, status=self.status,
                               status_info=self.status_info, status_change=self.last_status_change)
            HostLog.objects.filter(pk__in=HostLog.objects.filter(host=self).order_by('-status_change')
                               .values_list('pk')[MAX_LOG_LINES:]).delete()
        except Exception as ex:
            self.logger.warning('{:14} db saving error: {}, perhaps was deleted from database'.format(self.ipv4, ex))

    def check_and_update_host(self):
        '''The 'main' function of monitord, check/update host and logs'''
        now = timezone.now()
        self.last_check = now
        # Only update changed fields in DB
        update_fields = ['last_check']
        # Store old data before change it
        old_status_info = self.status_info
        self.check_ping()
        self.check_monitored_ports_status()
        #  if status info changed, update status and logs
        if old_status_info != self.status_info:
            self.logger.info('{:14} status info changed from "{}" to "{}"'
                              .format(self.ipv4, self.status_info.lower(), old_status_info.lower()))
            self.last_status_change = now
            update_fields.extend(['last_status_change', 'status', 'status_info'])
            self.update_log()
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

    def check_and_update_ports(self):
        pass


class HostLog(models.Model):
    '''Host Logs showed in host detail view'''
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
    is_monitored = models.BooleanField(default=False)
    counter_status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    counter_last_change = models.DateTimeField('last status change', default=timezone.now)
    error_counter = models.IntegerField(default=0)

    def update_log(self):
        '''Add new port log and remove old logs based on MAX_LOG_LINES'''
        try:
            PortLog.objects.create(port=self, counter_status=self.counter_status, 
                                   counter_last_change=self.counter_last_change,
                                   error_counter=self.error_counter)
            PortLog.objects.filter(pk__in=PortLog.objects.filter(port=self).order_by('-counter_last_change')
                                   .values_list('pk')[MAX_LOG_LINES:]).delete()
        except Exception as ex:
            self.logger.warning('{:14} db saving error: {}, perhaps was deleted from database'.format(self.ipv4, ex))

    def __str__(self):
        return self.number


class PortLog(models.Model):
    '''Port Logs showed in host detail view'''
    port = models.ForeignKey(Port, on_delete=models.CASCADE, null=True)
    counter_status = models.IntegerField(choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    counter_last_change = models.DateTimeField('last status change', default=timezone.now)
    error_counter = models.IntegerField(default=0)

    def __str__(self):
        return self.port.number