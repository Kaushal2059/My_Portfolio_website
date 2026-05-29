from django.shortcuts import render
from .models import About_me

def index(request):
    about = About_me.objects.first()
    return render(request, 'index.html', {"about": about})

def contact(request):
    return render(request, 'contact.html')

def projects(request):
    return render(request, 'projects.html')

def skills(request):
    return render(request, 'skills.html')