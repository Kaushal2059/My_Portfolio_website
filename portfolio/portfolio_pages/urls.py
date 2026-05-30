from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('contact/', views.contact, name = 'contact'), 
    path('projects/', views.projects, name = 'projects'),
    path('skills/', views.skills, name = 'skills' ),
    path('add_skill/', views.add_skill, name = 'add_skill' ),
    path('add_project/', views.add_project, name = 'add_project' ),
]