from django.views.generic import ListView, TemplateView
from .models import Host, Port, PortLog, Dio, Fiber, Status


class IndexView(TemplateView):
    template_name = "monitor/index.html"


class HostListView(ListView):
    template_name = "monitor/host_list.html"
    context_object_name = "host_list"

    def get_queryset(self):
        return Host.objects.all().order_by("-status", "-last_status_change")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = Status
        return context

class HostDetailView(TemplateView):
    template_name = "monitor/host_detail.html"

    def get_context_data(self, **kwargs):
        host = Host.objects.get(id=self.kwargs["pk"])
        portlog = PortLog.objects.filter(host=host)
        context = super(HostDetailView, self).get_context_data(**kwargs)
        context["host"] = host
        context["portlog"] = portlog
        return context


class PortView(TemplateView):
    template_name = "monitor/ports.html"


class PortListView(ListView):
    template_name = "monitor/port_list.html"
    context_object_name = "port_list"

    def get_queryset(self):
        return Port.objects.filter(
            counter_status__gt=2, error_counter__gt=500
        ).order_by("-counter_last_change", "-counter_status", "error_counter")


class DioListView(ListView):
    template_name = "monitor/dio_list.html"
    context_object_name = "dio_list"

    def get_queryset(self):
        return Dio.objects.all().order_by("pop", "name")


class DioDetailView(TemplateView):
    template_name = "monitor/dio_detail.html"

    def get_context_data(self, **kwargs):
        dio = Dio.objects.get(id=self.kwargs["pk"])
        fiber_list = Fiber.objects.filter(dio=dio).order_by("number")
        context = super(DioDetailView, self).get_context_data(**kwargs)
        context["dio"] = dio
        context["fiber_list"] = fiber_list
        return context
