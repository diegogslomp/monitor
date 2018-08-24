from django.contrib import admin
from .models import Host, Port


class PortInLines (admin.TabularInline):
    model = Port
    extra = 1
    classes = ['collapse']

class HostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['secretary', 'circuit', 'name', 'ipv4', 'network']}),
        ('Daemon Managed Status', {'fields': ['status', 'status_info', 'last_status_change', 'last_check'], 'classes': ['collapse']}),
    ]
    list_display =  ('ipv4', 'name', 'secretary', 'circuit', 'network', 'status')
    search_fields = ['ipv4', 'name', 'secretary', 'circuit', 'network', 'status']
    inlines = [PortInLines]
    actions = None

admin.site.register(Host, HostAdmin)
