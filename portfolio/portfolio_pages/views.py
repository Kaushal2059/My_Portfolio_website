from django.shortcuts import render
from .models import About_me, MY_Project, My_skill

def index(request):
    about = About_me.objects.first()
    return render(request, 'index.html', {"about": about})

def contact(request):
    return render(request, 'contact.html')

def projects(request):
    project = MY_Project.objects.all()
    return render(request, 'projects.html', {"projects": project})

def skills(request):
    skill = My_skill.objects.all()
    return render(request, 'skills.html', {"skills": skill})