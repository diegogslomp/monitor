from django.views.generic import DetailView, ListView, TemplateView
from monitor.models import Host, Port, PortLog

class IndexView(TemplateView):

    template_name = 'monitor/index.html'
    
class HostListView(ListView):

    template_name = 'monitor/host_list.html'
    context_object_name = 'host_list'

    def get_queryset(self):
        return Host.objects.all().order_by('-status', '-last_status_change')

class PortView(TemplateView):

    template_name = 'monitor/ports.html'

class PortListView(ListView):

    template_name = 'monitor/port_list.html'
    context_object_name = 'port_list'

    def get_queryset(self):
        return Port.objects.filter(counter_status__gt=2, error_counter__gt=50).order_by('-counter_last_change', '-counter_status', 'error_counter')

""" class DetailView(DetailView):

    template_name = 'monitor/detail.html'
    model = Host

 """
class DetailView(TemplateView):

    template_name = 'monitor/detail.html'

    def get_context_data(self, **kwargs):
        host = Host.objects.get(id=self.kwargs['pk'])
        portlog = PortLog.objects.filter(port__in=Port.objects.filter(host=host))
        context = super(DetailView, self).get_context_data(**kwargs)
        context['host'] = host
        context['portlog'] = portlog
        return context
