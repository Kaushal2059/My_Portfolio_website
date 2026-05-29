from django.contrib import admin
from .models import About_me, MY_Project, ProjectImage, My_skill

# Register your models here.
admin.site.register(About_me)
admin.site.register(My_skill)

class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 2

@admin.register(MY_Project)  
class MY_ProjectsAdmin(admin.ModelAdmin):
    inlines = [ProjectImageInline]
