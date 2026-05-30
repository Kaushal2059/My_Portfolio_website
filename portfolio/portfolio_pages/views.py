from django.shortcuts import render
from .models import About_me, MY_Project, My_skill, ProjectImage
from .forms import ContactForm, Add_skillForm, Add_ProjectForm
from django.shortcuts import get_object_or_404, redirect

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

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            Frst_name = form.cleaned_data["First_name"]
            Last_name = form.cleaned_data["Last_name"]
            Your_email = form.cleaned_data["Your_email"]
            role = form.cleaned_data["You_are"]
            message = form.cleaned_data["Message"]

    else:
        form = ContactForm()

    return render(request, "contact.html", {"form":form})

def add_skill(request):
    if request.method == "POST":
        form = Add_skillForm(request.POST ,request.FILES)

        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('skills')
    else:
        form = Add_skillForm()
    return render(request, "add_skill.html", {'form':form})

def add_project(request):
    if request.method == "POST":
        form = Add_ProjectForm(request.POST ,request.FILES)

        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()

            for image in request.FILES.getlist("images"):
                ProjectImage.objects.create(
                    project=project,
                    image=image
                )

            return redirect('projects')
    else:
        form = Add_ProjectForm()
    return render(request, "add_project.html", {'form':form})

   