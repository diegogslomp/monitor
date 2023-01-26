from django.contrib import admin
from .models import Host, Port, Fiber, Dio


class AbstractModelAdmin(admin.ModelAdmin):
    """Classe to dont repeat same fields to all"""

    actions = None
    list_per_page = 15


class PortInLines(admin.TabularInline):
    model = Port
    extra = 1
    classes = ["collapse"]


class HostAdmin(AbstractModelAdmin):
    fieldsets = [
        (
            None,
            {"fields": ["local", "circuit", "name", "ipv4", "network", "max_retries"]},
        ),
        (
            "Daemon Fields",
            {
                "fields": [
                    "status",
                    "status_info",
                    "last_status_change",
                    "last_check",
                    "retries",
                ],
                "classes": ["collapse"],
            },
        ),
    ]
    list_display = (
        "ipv4",
        "name",
        "local",
        "network",
        "status",
        "switch_manager",
        "max_retries",
        "circuit",
    )
    search_fields = ["ipv4", "name", "local", "circuit", "network", "status"]
    ordering = ("-switch_manager",)
    inlines = [PortInLines]


class FibraAdmin(AbstractModelAdmin):
    model = Fiber
    list_display = ("dio", "get_pop", "number", "port", "description")
    search_fields = ["dio__name", "number", "port", "description"]
    actions = None

    def get_pop(self, obj):
        return obj.dio.pop

    get_pop.short_description = "Pop"


class FibraInLines(admin.TabularInline):
    model = Fiber


class DioAdmin(AbstractModelAdmin):
    list_display = ("name", "pop")
    search_fields = ["name", "pop__name"]
    inlines = [FibraInLines]


class PortAdmin(AbstractModelAdmin):
    list_display = (
        "host",
        "ip_",
        "number",
        "error_counter",
        "counter_last_change",
        "is_monitored",
    )
    search_fields = ["host__name", "host__ipv4", "number"]
    ordering = ("-counter_last_change",)

    def ip_(self, obj):
        return obj.host.ipv4


admin.site.register(Host, HostAdmin)
admin.site.register(Dio, DioAdmin)
admin.site.register(Fiber, FibraAdmin)
admin.site.register(Port, PortAdmin)
