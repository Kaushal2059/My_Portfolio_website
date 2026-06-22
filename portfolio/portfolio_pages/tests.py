from django.test import TestCase, Client
from django.contrib.auth.models import User

# Create your tests here.
class Smoketest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username ='testuser',
            password='testpass2'
        )
            
    def test_homepage_loads(self):
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 301, 302])

    def test_admin_page_loads(self):
        response = self.client.get('/admin/')
        self.assertIn(response.status_code, [200, 302])

    def test_database_works(self):
        count = User.objects.count()
        self.assertGreaterEqual(count, 1)
    
    def test_authenticated_admin(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/admin/')
        self.assertIn(response.status_code, [200, 302])