from django.views.generic import DetailView, ListView, TemplateView
from monitor.models import Host, Log, Port

class IndexView(TemplateView):

    template_name = 'monitor/index.html'
    
class HostListView(ListView):

    template_name = 'monitor/host_list.html'
    context_object_name = 'host_list'

    def get_queryset(self):
        return Host.objects.all().order_by('-status', '-last_status_change')


class DetailView(DetailView):

    template_name = 'monitor/detail.html'
    model = Host
