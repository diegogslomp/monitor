from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.utils import DatabaseError
from monitor.models import Log, Host, Port
from monitor.settings import DAYS_FROM_DANGER_TO_WARNING, WAIT_FOR_NEXT, MAX_LOG_LINES
from monitor.settings import USER, PASSWORD
from telnetlib import Telnet
import subprocess
import time
import datetime
import logging


class Command(BaseCommand):
    args = ''
    help = 'Monitor Daemon for Monitor hosts'

    def handle(self, *args, **options):

        logger = logging.getLogger(__name__)
        logger.info('Monitord started')

        self.stdout.write(__name__)
        logger.debug("test debug ok")
