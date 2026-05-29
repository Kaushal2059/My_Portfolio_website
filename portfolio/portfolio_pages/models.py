from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class About_me(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(max_length= 240)
    image = models.ImageField(upload_to='photos/', blank = True, null= True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title