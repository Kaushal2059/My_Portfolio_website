from django import forms 
from .models import My_skill, MY_Project

class ContactForm(forms.Form):
    First_Name = forms.CharField(max_length = 100)
    Last_name = forms.CharField(max_length = 100)
    Your_email = forms.EmailField(required=True)
    Role = [("s","Student"), ("e", "Employer"), ("o","others")]
    You_are = forms.ChoiceField(choices=Role)
    Message = forms.CharField(max_length= 500, required=True, widget=forms.Textarea)
    
class Add_skillForm(forms.ModelForm):  
    class Meta:
        model = My_skill
        fields = ("title","description","image")

class Add_ProjectForm(forms.ModelForm):  
    class Meta:
        model = MY_Project
        fields = ("title","content")
