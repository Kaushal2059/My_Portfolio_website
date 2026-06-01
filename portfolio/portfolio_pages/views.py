from django.shortcuts import render
from .models import About_me, MY_Project, My_skill, ProjectImage
from .forms import ContactForm, Add_skillForm, Add_ProjectForm
from django.shortcuts import get_object_or_404, redirect
import sweetify

def index(request):
    about = About_me.objects.first()
    return render(request, 'index.html', {"about": about})

# def contact(request):
#     return render(request, 'contact.html')

def projects(request):
    project = MY_Project.objects.all()
    return render(request, 'projects.html', {"projects": project})

def skills(request):
    skill = My_skill.objects.all()
    return render(request, 'skills.html', {"skills": skill})

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            sweetify.success(request, "Your form has been submitted succesfully.")
            return redirect('contact')

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

def edit_skill(request, skill_id):
    skill = get_object_or_404(My_skill, pk = skill_id, user = request.user)
    if request.method == "POST":
        form = Add_skillForm(request.POST, request.FILES, instance=skill)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('skills')
    else:
        form = Add_skillForm(instance=skill)
    return render(request, "add_skill.html", {'form':form})

def delete_skill(request, skill_id):
    skill = get_object_or_404(My_skill, pk= skill_id, user = request.user)
    if request.method == "POST":
        skill.delete()
        return redirect('skills')
    return render(request, 'confirm_delete.html',{'object': skill, 'object_type': 'skill'})

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

def edit_project(request, project_id):
    project = get_object_or_404(MY_Project, pk=project_id, user = request.user)
    if request.method == "POST":
        form = Add_ProjectForm(request.POST, request.FILES, instance= project)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            return redirect('projects')
    else:
        form = Add_ProjectForm(instance=project)
    return render(request, 'add_project.html', {'form': form})

def delete_project(request, project_id):
    project = get_object_or_404(MY_Project, pk= project_id, user = request.user)
    if request.method == "POST":
        project.delete()
        return redirect('projects')
    return render(request, 'confirm_delete.html',{'object': project, 'object_type': 'project'})