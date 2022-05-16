from django.core.management.base import BaseCommand
from monitor.models import Host
import logging
import sys


class Command(BaseCommand):
    args = ''
    logger = logging.getLogger(__name__)
    help = 'Show gateways from all hosts'

    def main(self):

        for host in Host.objects.all():
            if host.status == host.SUCCESS:
                gateway = str(host.telnet_gateway())
                sys.stdout.write('{:15} - {:15} - {}\n'.format(host.ipv4, gateway, host.name))

    def handle(self, *args, **options):
        self.logger.info('Show gateways started')
        self.main()
