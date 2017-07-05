from django.core.management.base import BaseCommand
from django.core import serializers
import urllib.request, json

from monitor.models import Host, Log, Port

class Command(BaseCommand):

 args = ''
 help = 'Populate db from json url'

 def handle(self, *args, **options):
     models = ('hosts','logs','ports')
     for model in models:
         json_url = "http://localhost:8080/monitor/{0}/json/".format(model)
         with urllib.request.urlopen(json_url) as url:
             data = json.loads(url.read().decode())
             for deserialized_obj in serializers.deserialize("json", data):
                 deserialized_obj.save()
         self.stdout.write("{0} imported to database!".format(model))
