import datetime
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase

from .models import Host

class HostModelTest(TestCase):
    def test_host_status(self):
        """
        Test a "pingable" host
        """
        active_host = Host(name='local', ipv4='127.0.0.1')
        self.assertEqual(Host.DEFAULT, active_host.status)
        active_host.check_ping()
        self.assertEqual(Host.SUCCESS, active_host.status)

class HostListViewTests(TestCase):
    def test_no_host_list(self):
        """
        If no hosts exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse('monitor:host_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hosts are available.")
        self.assertQuerysetEqual(response.context['host_list'], [])
