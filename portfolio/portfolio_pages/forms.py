from django import forms 
from .models import My_skill, MY_Project, Contact

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ("Name","Your_email","You_are", "Message")
    
class Add_skillForm(forms.ModelForm):  
    class Meta:
        model = My_skill
        fields = ("title","description","image")

class Add_ProjectForm(forms.ModelForm):  
    class Meta:
        model = MY_Project
        fields = ("title","content")
