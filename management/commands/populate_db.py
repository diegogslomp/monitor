from django.core.management.base import BaseCommand

from monitor.models import Host
import csv

class Command(BaseCommand):

    args = ''
    help = 'Get switches from <csvfile>'

    def add_arguments(self, parser):
        parser.add_argument('<csvfile>')

    def handle(self, *args, **options):
        with open(options['<csvfile>'], 'r', newline='') as csvfile:
            next(csvfile)
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                host, created = Host.objects.get_or_create(ipv4=row[0])
                host.name = row[10]
                host.description = '{0} - {1}'.format(row[8], row[11])
                host.save()
                self.stdout.write("{0} info added to monitor".format(row[0]))
