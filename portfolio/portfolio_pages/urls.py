from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('contact/', views.contact, name = 'contact'), 
    path('projects/', views.projects, name = 'projects'),
    path('skills/', views.skills, name = 'skills' ),
    path('add_skill/', views.add_skill, name = 'add_skill' ),
    path('<int:skill_id>/edit_skill/', views.edit_skill, name = 'edit_skill' ),
    path('<int:skill_id>/delete_skill/', views.delete_skill, name = 'delete_skill' ),
    path('add_project/', views.add_project, name = 'add_project' ),
    path('<int:project_id>/edit_project/', views.edit_project, name = 'edit_project' ),
    path('<int:project_id>/delete_project/', views.delete_project, name = 'delete_project' ),
    path('resume/', views.resume, name = 'resume' ),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
    