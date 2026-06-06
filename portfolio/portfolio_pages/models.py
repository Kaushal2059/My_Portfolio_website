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
    
class MY_Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default = 1)
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)  # fix: auto_now_add for created
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.content}"

    def primary_image(self):
        return self.images.first()  # helper to grab first image


class ProjectImage(models.Model):
    project = models.ForeignKey(MY_Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='photos/')
    caption = models.CharField(max_length=100, blank=True)  
    order = models.PositiveIntegerField(default=0)           
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.project.title}"
    
class Projecttech_stack(models.Model):
    project = models.ForeignKey(MY_Project, on_delete=models.CASCADE, related_name= "tech_stack")
    tech_stack = models.CharField(max_length=50, null=False, blank= False)

    def __str__(self):
        return self.tech_stack
    
    
class My_skill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default = 1)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=250)
    image = models.ImageField(upload_to='photos/')

    def __str__(self):
        return self.title
    
class Contact(models.Model):
    Name = models.CharField(max_length = 100)
    Your_email = models.EmailField(blank=False, null= False, max_length=254)
    Role = [("s","Student"), ("e", "Employer"), ("o","others")]
    You_are = models.CharField(choices=Role, max_length=1)
    Message =models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # fix: auto_now_add for created
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.Name} wants to say -------- {self.Message[:50]}"