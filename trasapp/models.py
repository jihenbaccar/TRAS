from django.db import models

# Create your models here.

DIFFICULTY_CHOICES = [
    ('Easy', 'Easy'),
    ('Medium', 'Medium'),
    ('Hard', 'Hard'),
]

class Word(models.Model):
    word = models.CharField(max_length=50)
    image = models.ImageField(upload_to='images/')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Easy')

    def __str__(self):
        return self.word


class Story(models.Model):
    title = models.CharField(max_length=255)
    pdf = models.FileField(upload_to='stories/pdfs/')
    audio_files = models.JSONField(default=list, null=True, blank=True)  # Stores audio file paths for each page
    questions = models.JSONField(default=list, null=True, blank=True)

    def __str__(self):
        return self.title

        