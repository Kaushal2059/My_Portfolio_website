from django.contrib import admin
from .models import About_me, MY_Project, ProjectImage, My_skill, Contact, Projecttech_stack

# Register your models here.
admin.site.register(About_me)
admin.site.register(My_skill)

class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 2

class Projecttech_stackInlin(admin.TabularInline):
    model = Projecttech_stack
    extra = 2

@admin.register(MY_Project)  
class MY_ProjectsAdmin(admin.ModelAdmin):
    inlines = [ProjectImageInline, Projecttech_stackInlin]

@admin.register(Contact)
class Contactadmin(admin.ModelAdmin):
    readonly_fields = ('Name', 'Your_email', 'You_are', 'Message', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False