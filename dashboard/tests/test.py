from django.test import TestCase
from django.urls import resolve
from dashboard.views import index
from django.http import HttpRequest

class DashboardPageTest(TestCase):

    def setup(self):
        self.view = DashboardPageTest()

    def test_dashboard_url_resolves_to_dashboard_view(self):
        found = resolve('/')
        self.assertEqual(found.func,index)

'''

    def test_dashboard_url_returns_correct_template(self):
        request = HttpRequest()  
        response = index(request)  
        html = response.content.decode('utf8')  
        self.assertTrue(html.startswith('<html>'))  
        self.assertIn('<title></title>', html)  
        self.assertTrue(html.endswith('</html>'))  
'''