from django import forms
from .models import Story

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['title', 'pdf', 'audio_files', 'questions']

    questions = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'JSON format of questions'}))
