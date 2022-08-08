from xmlrpc.client import Boolean
from django.db import models
from django.utils import timezone
import datetime
import logging
import re
import subprocess
import telnetlib
import os

class Host(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    ipv4 = models.GenericIPAddressField(protocol='IPv4')
    last_check = models.DateTimeField('last check', default=timezone.now)
    last_status_change = models.DateTimeField(
        'last status change', default=timezone.now)
    status_info = models.CharField(max_length=200, blank=True, default='')
    network = models.GenericIPAddressField(
        protocol='IPv4', null=True, blank=True)
    circuit = models.IntegerField(null=True, blank=True)
    retries = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=0)
    local = models.CharField(max_length=200, null=True, blank=True)
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
    def is_pinging(self):
        return not subprocess.call(f'ping -4 -c 3 -w 1 -W 5 {self.ipv4} | grep ttl= >/dev/null 2>&1', shell=True)

    def send_telegram_message(self):
        token = os.getenv('TELEGRAM_TOKEN', '')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        if token == '' or chat_id == '':
            self.log('To send telegram messages, TELEGRAM_TOKEN e TELEGRAM_CHAT_ID must be declared', 'warning')
        else:
            url=f'https://api.telegram.org/bot{token}/sendMessage'
            icon = '\u2705' if self.status < self.WARNING else '\u274C'
            message = f'{icon} {self.name} - {self.status_info}'
            self.log(message, 'info')
            subprocess.call(f'curl -s -X POST {url} -d chat_id={chat_id} -d text="{message}" >/dev/null 2>&1', shell=True)

    def log(self, message, level='debug'):
        log_message = f'{self.ipv4:14} {message}'
        if level == 'info':
            self.logger.info(log_message)
        elif level == 'warning':
            self.logger.warning(log_message)
        else:
            self.logger.debug(log_message)

    def telnet_monitored_ports_and_update_status(self):
        '''Filter telnet manually added monitored ports'''

        # Only check ports if online and has ports to be monitored
        if self.status == self.SUCCESS and self.monitored_ports.count() > 0:

            ports = ';'.join([port.number for port in self.monitored_ports])
            show_port_status = f'show port status {ports}'
            telnet_output = self.telnet(show_port_status)
            if not telnet_output:
                self.status = self.DANGER
                self.status_info = 'Telnet: Can\'t get port status'
            else:
                for line in telnet_output:
                    if re.search(r'[no ,in]valid', line):
                        self.status = self.DANGER
                        self.status_info = 'Invalid port registered or module is Down'
                        self.log(self.status_info, 'warning')
                        continue
                    for port in self.monitored_ports:
                        if re.search(r'{} .*down'.format(port.number), line):
                            self.status = self.DANGER
                            alias = line.split()[1]
                            msg = f'Port {port.number} ({alias}) is Down'
                            if self.status_info == 'Up':
                                self.status_info = msg
                            else:
                                self.status_info += f', {msg}'
                            self.log(self.status_info)

    def telnet_port_counters(self):
        '''Filter telnet port counters, create ports and change status'''
        if self.status == self.SUCCESS:
            now = timezone.now()
            telnet_output = self.telnet('show port counters')
            if telnet_output:
                port_object = None
                for line in telnet_output:
                    # Create port if not exists
                    if re.search(r'^port:', line):
                        port_number = line.split()[1]
                        self.log(f'Filtered Port: {port_number}')
                        port_object = Port.objects.get_or_create(
                            host=self, number=port_number)[0]
                    elif re.search(r'^port :', line):
                        port_number = line.split()[2]
                        self.log(f'Filtered Port: {port_number}')
                        port_object = Port.objects.get_or_create(
                            host=self, number=port_number)[0]
                    # Update counter and status
                    elif re.search(r'^in errors', line):
                        error_counter = int(line.split()[2])
                        self.log(f'Filtered Counter: {error_counter}')
                        self.log(f'Old Counter: {port_object.error_counter}')
                        # Only save updated fields
                        update_fields = []
                        # If conter updated, change var and status
                        if error_counter != port_object.error_counter:
                            port_object.error_counter = error_counter
                            port_object.counter_last_change = now
                            port_object.counter_status = Host.DANGER
                            update_fields.extend(
                                ['error_counter', 'counter_last_change', 'counter_status'])
                            # Add port log if counter changed
                            port_object.update_log()
                            self.log(f'Counter updated to: {error_counter}')
                        else:
                            old_counter_status = port_object.counter_status
                            delta_1_day = now - datetime.timedelta(days=1)
                            if port_object.counter_last_change <= delta_1_day:
                                port_object.counter_status = self.WARNING
                            delta_5_days = now - datetime.timedelta(days=5)
                            if port_object.counter_last_change <= delta_5_days:
                                port_object.counter_status = self.SUCCESS
                            if old_counter_status != port_object.counter_status:
                                update_fields.extend(['counter_status'])
                        if len(update_fields) > 0:
                            try:
                                port_object.save(update_fields=update_fields)
                                self.log('Save port log to database')
                            except Exception as ex:
                                self.log(ex, 'warning')
                        port_object = None

    def telnet_gateway(self):
        '''Filter gateway from telnet output'''
        if self.status == self.SUCCESS:
            telnet_output = self.telnet('show ip route')
            if telnet_output:
                for line in telnet_output:
                    if re.search(r'0.0.0.0', line):
                        self.log(f'Gateway telnet line: {line}')
                        if re.search('^\s*s', line):
                            gateway = line.split()[4]
                        else:
                            gateway = line.split()[1]
                        self.log(f'Filtered gateway: {gateway}')
                        return gateway

    def telnet(self, command):
        '''Telnet connection and get registered ports status'''
        self.log('Telnet started')
        telnet_output = []
        timeout = os.getenv('TELNET_TIMEOUT', 5)
        user = os.getenv('TELNET_USER', 'admin')
        password = os.getenv('TELNET_PASSWORD', '')
        try:
            with telnetlib.Telnet(self.ipv4, timeout=timeout) as tn:
                tn.read_until(b"Username:", timeout=timeout)
                tn.write(user.encode('ascii') + b"\n")
                tn.read_until(b"Password:", timeout=timeout)
                tn.write(password.encode('ascii') + b"\n")
                # '->' for successful login or 'Username' for wrong credentials
                match_object = tn.expect([b"->", b"Username:"], timeout=timeout)
                expect_match = match_object[1].group(0)
                self.log(f'Match: {expect_match}')
                if expect_match == b"Username:":
                    raise Exception('invalid credentials')
                else:
                    self.log(command)
                    tn.write(command.encode('ascii') + b"\n")
                    tn.write(b"exit\n")
                    self.log('Telnet finished')
                    telnet_output = tn.read_all().decode('ascii').lower().replace('\r', '').split('\n')
        except Exception as ex:
            self.log(f'Telnet: {ex}', 'warning')
        finally:
            return telnet_output

    def ping_and_update_status(self):
        '''Ping host, then telnet if there are registered ports'''
        if self.is_pinging:
            self.status = self.SUCCESS
            self.status_info = 'Up'
        else:
            self.status = self.DANGER
            self.status_info = 'Down'
        self.log(self.status_info)

    def update_log(self):
        '''Add new host log and remove old logs based on MAX_LOG_LINES'''
        try:
            max_log_lines = os.getenv('MAX_LOG_LINES', 20)
            HostLog.objects.create(host=self, status=self.status,
                                   status_info=self.status_info, status_change=self.last_status_change)
            HostLog.objects.filter(pk__in=HostLog.objects.filter(host=self).order_by('-status_change')
                                   .values_list('pk')[max_log_lines:]).delete()
            self.send_telegram_message()
        except Exception as ex:
            self.log(ex, 'warning')

    def check_and_update(self):
        '''The 'main' function of monitord, check/update host and logs'''
        now = timezone.now()
        self.last_check = now
        # Only update changed fields in DB
        update_fields = ['last_check']
        # Store old data before change it
        old_status = self.status
        old_status_info = self.status_info
        self.ping_and_update_status()
        self.telnet_monitored_ports_and_update_status()
        # Update log only if retries reach max_retires
        if self.status == self.DANGER and self.retries < self.max_retries:
            self.retries += 1
            update_fields.extend(['retries'])
            self.log(f'{self.retries}/{self.max_retries} retry', 'warning')
        else:
            # if online, reset retries
            if self.status == self.SUCCESS:
                self.retries = 0
                update_fields.extend(['retries'])
            # if status info changed, update status and logs
            if old_status_info != self.status_info:
                self.log(f'Status info changed from "{old_status_info}" to "{self.status_info}"')
                self.last_status_change = now
                update_fields.extend(
                    ['last_status_change', 'status', 'status_info'])
                self.update_log()
            # check if change the status from danger to warning status
            elif self.status == self.DANGER:
                days_to_warning = os.getenv('DAYS_FROM_DANGER_TO_WARNING', 5)
                delta_limit_to_warning_status = now - \
                    datetime.timedelta(days=days_to_warning)
                if self.last_status_change <= delta_limit_to_warning_status:
                    self.status = self.WARNING
                    update_fields.extend(['status'])
        # Save only if the host was not deleted while in buffer
        try:
            self.save(update_fields=update_fields)
        except Exception as ex:
            self.log(ex, 'warning')


class HostLog(models.Model):
    '''Host Logs showed in host detail view'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    status = models.IntegerField(
        choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return self.host.name


class Port(models.Model):
    '''Ports used to check status using telnet'''
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    is_monitored = models.BooleanField(default=False)
    counter_status = models.IntegerField(
        choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    counter_last_change = models.DateTimeField(
        'last status change', default=timezone.now)
    error_counter = models.IntegerField(default=0)
    logger = logging.getLogger(__name__)

    def log(self, message, level='debug'):
        log_message = f'{self.host.ipv4:14} {message}'
        if level == 'info':
            self.logger.info(log_message)
        elif level == 'warning':
            self.logger.warning(log_message)
        else:
            self.logger.debug(log_message)

    def update_log(self):
        '''Add new port log and remove old logs based on MAX_LOG_LINES'''
        try:
            max_log_lines = os.getenv('MAX_LOG_LINES', 20)
            PortLog.objects.create(port=self, host=self.host, counter_status=self.counter_status,
                                   counter_last_change=self.counter_last_change,
                                   error_counter=self.error_counter)
            PortLog.objects.filter(pk__in=PortLog.objects.filter(port=self).order_by('-counter_last_change')
                                   .values_list('pk')[max_log_lines:]).delete()
        except Exception as ex:
            self.log(ex, 'warning')

    def __str__(self):
        return self.number


class PortLog(models.Model):
    '''Port Logs showed in host detail view'''
    port = models.ForeignKey(Port, on_delete=models.CASCADE, null=True)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True)
    counter_status = models.IntegerField(
        choices=Host.STATUS_CHOICES, default=Host.DEFAULT)
    counter_last_change = models.DateTimeField(
        'last status change', default=timezone.now)
    error_counter = models.IntegerField(default=0)

    def __str__(self):
        return self.port.number


class Dio(models.Model):
    '''DIO Bastidor Optico'''
    pop = models.ForeignKey(Host, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Fibra(models.Model):
    '''Portas/Fibras dos DIO'''
    dio = models.ForeignKey(Dio, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    port = models.CharField(max_length=20, blank=True, default='')
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.number
