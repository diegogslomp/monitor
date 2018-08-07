from django.views import generic
from monitor.models import Host, Log, Port

class IndexView(generic.ListView):

    template_name = 'monitor/index.html'
    context_object_name = 'host_list'

    def get_queryset(self):
        return Host.objects.all().order_by('-status', '-last_status_change')

class HostListView(generic.ListView):

    template_name = 'monitor/host_list.html'
    context_object_name = 'host_list'

    def get_queryset(self):
        return Host.objects.all().order_by('-status', '-last_status_change')


class DetailView(generic.DetailView):

    template_name = 'monitor/detail.html'
    model = Host
