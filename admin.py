from django.contrib import admin
from .models import Host, Port, Dio, Fibra


class PortInLines (admin.TabularInline):
    model = Port
    extra = 1
    classes = ['collapse']


class HostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['secretary',
                           'circuit', 'name', 'ipv4', 'network']}),
        ('Daemon Managed Status', {'fields': [
         'status', 'status_info', 'last_status_change', 'last_check'], 'classes': ['collapse']}),
    ]
    list_display = ('ipv4', 'name', 'secretary',
                    'circuit', 'network', 'status')
    search_fields = ['ipv4', 'name', 'secretary',
                     'circuit', 'network', 'status']
    inlines = [PortInLines]
    actions = None
    list_per_page = 15


class FibraInLines(admin.TabularInline):
    model = Fibra


class DioAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = ('name', 'pop')
    inlines = [FibraInLines]


class PortAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = ('host', 'number', 'error_counter', 'counter_last_change',)
    ordering = ('-counter_last_change',)
    actions = None


admin.site.register(Host, HostAdmin)
admin.site.register(Dio, DioAdmin)
admin.site.register(Port, PortAdmin)
