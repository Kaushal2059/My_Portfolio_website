from django.shortcuts import render
from .models import About_me, MY_Project, My_skill, ProjectImage, Projecttech_stack
from .forms import ContactForm, Add_skillForm, Add_ProjectForm
from django.shortcuts import get_object_or_404, redirect
import sweetify
from django.conf import settings
from django.core.mail import send_mail

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
            submit = form.save()

            # --- Build the email ---
            role_display = submit.get_You_are_display()  # converts 's' → 'Student' etc.
            subject = f"New Contact Form submit from {submit.Name}"
            message = f"""
You have a new contact form submit on your portfolio.

-----------------------------
Name    : {submit.Name}
Email   : {submit.Your_email}
Role    : {role_display}
-----------------------------

Message:
{submit.Message}

Submitted at: {submit.created_at.strftime("%B %d, %Y at %I:%M %p")}
            """

            # --- Send the email ---
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,   # Won't crash the site if email fails
            )

            sweetify.success(request, "Your message has reached to Kaushal succesfully.")
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
            
            tech = request.POST.get("tech_stack")

            for techs in tech.split(","):
                techs = techs.strip()

                if techs:
                    Projecttech_stack.objects.create(
                        project=project,
                        tech_stack=techs
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

            tech = request.POST.get("tech_stack")
            if tech:
                for techs in tech.split(","):
                    techs = techs.strip()
                    if techs:
                        Projecttech_stack.objects.create(
                            project=project,
                            tech_stack=techs
                        )
            return redirect('projects')
    else:
        form = Add_ProjectForm(instance=project)
    return render(request, 'add_project.html', {'form': form, 'project': project})

def delete_project(request, project_id):
    project = get_object_or_404(MY_Project, pk= project_id, user = request.user)
    if request.method == "POST":
        project.delete()
        return redirect('projects')
    return render(request, 'confirm_delete.html',{'object': project, 'object_type': 'project'})