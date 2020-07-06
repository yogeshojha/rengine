from django.test import TestCase
from django.urls import resolve
from dashboard.views import index

class DashboardPageTest(TestCase):

    def setup(self):
        self.view = DashboardPageTest()

    def test_dashboard_url_resolves_to_dashboard_view(self):
        found = resolve('/')
        self.assertEqual(found.func,index)
