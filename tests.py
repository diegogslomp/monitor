import datetime
import logging
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase
import os
from .models import Host

logging.disable(logging.CRITICAL)

class HostModelTest(TestCase):
    def test_online_host(self):
        """
        Test a "pingable" host
        """
        online_host = Host(name='online', ipv4='127.0.0.1')
        self.assertEqual(Host.DEFAULT, online_host.status)
        online_host.check_and_update()
        self.assertEqual(Host.SUCCESS, online_host.status)

    def test_offline_host(self):
        """
        Test a offline host
        """
        offline_host = Host(
            name='offline',
            ipv4='7.7.7.7',
            status=Host.SUCCESS,
            status_info="Up"
            )
        offline_host.check_and_update()
        self.assertEqual(Host.DANGER, offline_host.status)

    def test_danger_to_warning_status_host(self):
        """
        Change host status after DAYS_FROM_DANGER_TO_WARNING
        """
        now = timezone.now()
        days_to_warning = os.getenv('DAYS_FROM_DANGER_TO_WARNING', 5)
        offline_host = Host(
            name='offline',
            ipv4='7.7.7.7',
            status=Host.DANGER,
            last_status_change = now - datetime.timedelta(days=days_to_warning),
            status_info = 'Down',
            max_retries = 0
            )
        offline_host.check_and_update()
        self.assertEqual(Host.WARNING, offline_host.status)


class HostListViewTests(TestCase):
    def test_empty_list(self):
        """
        If no hosts exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse('monitor:host_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hosts are available.")
        self.assertQuerysetEqual(response.context['host_list'], [])
