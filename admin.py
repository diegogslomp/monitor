from django.contrib import admin
from .models import Host, Port, Dio, Fibra


class AbstractModelAdmin(admin.ModelAdmin):
    '''Classe to dont repeat same fields to all'''
    actions = None
    list_per_page = 15


class PortInLines (admin.TabularInline):
    model = Port
    extra = 1
    classes = ['collapse']


class HostAdmin(AbstractModelAdmin):
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


class FibraAdmin(AbstractModelAdmin):
    model = Fibra
    list_display = ('dio', 'get_pop', 'number', 'port', 'description')
    search_fields = ['dio__name', 'number', 'port', 'description']
    actions = None

    def get_pop(self, obj):
        return obj.dio.pop
    get_pop.short_description = 'Pop'


class FibraInLines(admin.TabularInline):
    model = Fibra


class DioAdmin(AbstractModelAdmin):
    list_display = ('name', 'pop')
    search_fields = ['name', 'pop__name']
    inlines = [FibraInLines]


class PortAdmin(AbstractModelAdmin):
    list_display = ('host', 'number', 'error_counter', 'counter_last_change',)
    search_fields = ['host__name', ]
    ordering = ('-counter_last_change',)


admin.site.register(Host, HostAdmin)
admin.site.register(Dio, DioAdmin)
admin.site.register(Fibra, FibraAdmin)
admin.site.register(Port, PortAdmin)
