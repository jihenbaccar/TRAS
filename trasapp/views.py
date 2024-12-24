from django.http import JsonResponse
from django.shortcuts import render
from deepface import DeepFace
import cv2
import base64
from io import BytesIO
from PIL import Image
import numpy as np
import json 
from django.views.decorators.csrf import csrf_exempt
from gtts import gTTS
import os
import speech_recognition as sr
from .models import Word
import random
from django.conf import settings



# FACIAL EXPRESSIONS DETECTION CODE

def facial_expression_view(request):
    if request.method == "POST":
        # Capture the video frame from the POST request
        video_capture = cv2.VideoCapture(0)  # Use the default camera
        
        ret, frame = video_capture.read()
        if not ret:
            return JsonResponse({"error": "Could not capture video frame"}, status=400)
        
        # Analyze facial expression
        try:
            result = DeepFace.analyze(frame, actions=['emotion'])
            detected_emotion = result[0]['dominant_emotion']
            
            # Check if the detected expression matches the required one
            required_expression = request.POST.get("required_expression")
            if detected_emotion.lower() == required_expression.lower():
                return JsonResponse({"success": True, "message": "Expression matched!"})
            else:
                return JsonResponse({"success": False, "message": "Expression did not match.", "detected": detected_emotion})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            video_capture.release()
    else:
        return render(request, 'facial_expression.html')

@csrf_exempt  # To handle POST requests without CSRF token (use carefully in production)
def check_expression(request):
    if request.method == "POST":
        data = json.loads(request.body)
        required_expression = data['required_expression'].lower().strip()  # Convert to lowercase and strip spaces
        frame = data['frame']  # The base64 image from the frontend
        
        # Decode the base64 image
        img_data = base64.b64decode(frame.split(",")[1])  # Remove the header part of base64 string
        img = Image.open(BytesIO(img_data))

        # Convert the image to a numpy array that DeepFace can use
        img = np.array(img)
        
        # If the image has an alpha channel (transparency), we remove it
        if img.shape[-1] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

        # Define the emotion map to handle variations in DeepFace's predicted emotion
        emotion_map = {
            "surprise": "surprised",
            "neutral": "neutral",
            "happy": "happy",
            "sad": "sad",
            "angry": "angry",
            # Add other mappings here if necessary
        }

        try:
            # Analyze the image for emotion
            result = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)
            
            # Extract the predicted emotion (ensure it's in the correct format)
            predicted_emotion = result[0]['dominant_emotion'].lower().strip()  # Convert to lowercase and strip spaces
            
            # Use the emotion map to normalize any variations (like 'surprise' -> 'surprised')
            predicted_emotion = emotion_map.get(predicted_emotion, predicted_emotion)

            # Check if the predicted emotion matches the required expression
            if predicted_emotion == required_expression:
                response = {"message": "Correct expression!"}
            else:
                response = {"message": f"Incorrect expression! You made a {predicted_emotion}."}
            
        except Exception as e:
            response = {"message": f"Error: {str(e)}"}
        
        return JsonResponse(response)

    return JsonResponse({"message": "Invalid request method."}, status=400)



# PRONUNCIATION CORRECTION CODE

@csrf_exempt
def get_word(request):
    # Get a random word and its associated image
    words = list(Word.objects.all())
    word = random.choice(words)
    return JsonResponse({'word': word.word, 'image': word.image.url})

@csrf_exempt
def speak_word(request):
    # Receive word data, generate speech, and return audio file path
    data = json.loads(request.body)
    word = data.get('word')
    tts = gTTS(text=word, lang='en')
    audio_path = f'media/audio/{word}.mp3'  # Save audio to 'media/audio/{word}.mp3'
    tts.save(audio_path)
    return JsonResponse({'audio_path': audio_path})

import os
import speech_recognition as sr
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment  # For converting audio files to WAV format

import wave

@csrf_exempt
def assess_pronunciation(request):
    if request.method == 'POST':
        # Receive audio file and expected word
        audio_file = request.FILES['audio']
        expected_word = request.POST['expected_word']

        # Check if the uploaded file is a valid WAV file
        try:
            with wave.open(audio_file, 'rb') as wf:
                # Verify that the file is a valid WAV and has the correct format
                if wf.getsampwidth() != 2:  # Check sample width (16-bit PCM is standard)
                    raise ValueError("Invalid WAV format. Expected 16-bit PCM WAV.")
                if wf.getnchannels() != 1:  # Ensure mono audio
                    raise ValueError("Invalid WAV format. Expected mono audio.")
        except Exception as e:
            return JsonResponse({'feedback': f"Invalid audio file: {str(e)}"})

        # Proceed with transcription and comparison as before
        # Save the uploaded audio temporarily
        audio_path = 'temp_audio.wav'
        with open(audio_path, 'wb') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        # Transcribe audio using speech recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        try:
            transcription = recognizer.recognize_google(audio).lower()
            if transcription == expected_word.lower():
                feedback = "Correct!"
            else:
                feedback = f"Incorrect. You said '{transcription}', but the correct word is '{expected_word}'."
        except sr.UnknownValueError:
            feedback = "Could not understand your pronunciation. Please try again."

        if os.path.exists(audio_path):
             os.remove(audio_path)

        return JsonResponse({'feedback': feedback})



def pronunciation_view(request):
    # Fetch a random word from the database
    word = Word.objects.order_by('?').first()  # Random word

    if word:
        # Construct the image URL for the word
        image_url = word.image.url  # The image path stored in the database
    else:
        word = "No Word Found"  # Default word if none is found
        image_url = "/media/images/default.jpg"  # Fallback image if no image is found

    # Pass the word and image URL to the template
    return render(request, 'pronunciation.html', {'word': word.word, 'image_url': image_url})




#  STORY READING CODE


import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from gtts import gTTS
import fitz  # PyMuPDF
from .models import Story

from PIL import Image
import pytesseract
import io



import os
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from gtts import gTTS
import fitz  # PyMuPDF
from .models import Story

# Extract text from a PDF where the text is selectable
def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    pages_text = [page.get_text("text").strip() for page in document if page.get_text("text").strip()]
    document.close()
    return pages_text

# Generate audio files for each page of the story
def generate_audio_for_story(story):
    audio_files = []
    pages_text = extract_text_from_pdf(story.pdf.path)
    for i, text in enumerate(pages_text):
        audio_filename = f"story_{story.id}_page_{i + 1}.mp3"
        audio_path = os.path.join(settings.MEDIA_ROOT, 'stories', 'audio', audio_filename)
        tts = gTTS(text, lang='en')
        tts.save(audio_path)
        audio_files.append(audio_filename)
    story.audio_files = audio_files
    story.save()

# Serve audio files
def serve_audio(request, filename):
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'stories', filename)
    if os.path.exists(audio_file_path):
        with open(audio_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type="audio/mpeg")
            response['Content-Disposition'] = f'inline; filename={filename}'
            return response
    return HttpResponse(status=404)

# Story detail view
def story_detail(request, story_id):
    # Fetch the story object
    story = get_object_or_404(Story, pk=story_id)

    # If the story does not have audio files, regenerate them
    if not story.audio_files:
        generate_audio_for_story(story)

    # Construct the full URL for the PDF
    pdf_url = settings.MEDIA_URL + str(story.pdf)
    audio_files = story.audio_files  # Get the audio files from the database
    questions = story.questions  # Get the quiz questions from the database

    # Render the HTML template with the story data and PDF URL
    return render(request, 'story_detail.html', {'story': story, 'pdf_url': pdf_url, 'audio_files': audio_files, 'questions': questions})



def check_answer(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    question_index = int(request.GET.get('question_index'))
    user_answer = request.GET.get('answer')
    correct_answer = story.questions[question_index]["correct_answer"]

    response_data = {
        'result': user_answer == correct_answer,
        'correct_answer': correct_answer if user_answer != correct_answer else None,
    }
    return JsonResponse(response_data)



#STORY Management
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def manage_stories(request):
    stories = Story.objects.all()
    return render(request, 'manage_stories.html', {'stories': stories})

def add_story(request):
    if request.method == 'POST':
        title = request.POST.get('name')
        pdf = request.FILES.get('pdf')
        quiz_questions = request.POST.get('quiz_questions')

        try:
            quiz_questions = json.loads(quiz_questions) if quiz_questions else []
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON for quiz questions.'})

        if not title or not pdf:
            return JsonResponse({'status': 'error', 'message': 'Missing title or PDF file.'})

        story = Story.objects.create(title=title, pdf=pdf, questions=quiz_questions)
        return JsonResponse({'status': 'success', 'story': {'id': story.id, 'name': story.title}})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


def update_story(request, story_id):
    story = get_object_or_404(Story, id=story_id)

    if request.method == 'POST':
        title = request.POST.get('name')
        pdf = request.FILES.get('pdf')
        quiz_questions = request.POST.get('quiz_questions')

        # Handle quiz questions (if any)
        try:
            quiz_questions = json.loads(quiz_questions) if quiz_questions else []
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON for quiz questions.'})

        # Update the story's title
        if title:
            story.title = title
        
        # If a new PDF is uploaded, process it
        if pdf:
            # Clear old audio files before saving the new PDF
            audio_folder = os.path.join(settings.MEDIA_ROOT, 'stories', 'audio')
            for filename in os.listdir(audio_folder):
                if filename.startswith(f"story_{story.id}_") and filename.endswith(".mp3"):
                    file_path = os.path.join(audio_folder, filename)
                    os.remove(file_path)

            # Save the new PDF and clear old audio files
            story.pdf = pdf
            story.audio_files= [] # Clear old audio files before generating new ones

        # Update quiz questions
        story.questions = quiz_questions
        story.save()  # Save the updated story

        return JsonResponse({'status': 'success', 'story': {'id': story.id, 'name': story.title}})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

def delete_story(request, story_id):
    try:
        # Get the story by ID
        story = get_object_or_404(Story, id=story_id)

        # Define the path to the audio folder
        audio_folder = os.path.join(settings.MEDIA_ROOT, 'stories', 'audio')

        # Delete audio files related to the story
        deleted_files = []
        for filename in os.listdir(audio_folder):
            if filename.startswith(f"story_{story.id}_") and filename.endswith(".mp3"):
                file_path = os.path.join(audio_folder, filename)
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                except Exception as e:
                    continue  # Ignore errors in deleting individual files

        # Delete the story itself
        story.delete()

        return JsonResponse({'status': 'success', 'message': 'Story and associated audios deleted successfully.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An error occurred while deleting the story'}, status=500)
    


# MANAGE WORDS

from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage

def manage_words(request):
    return render(request, 'manage_words.html')


@csrf_exempt
def get_words(request):
    """Fetch all words."""
    if request.method == 'GET':
        words = Word.objects.all()
        word_list = [
            {
                "id": word.id,
                "word": word.word,
                "image": word.image.url if word.image else "",  # Serialize the image URL
                "difficulty": word.difficulty,
            }
            for word in words
        ]
        return JsonResponse(word_list, safe=False)
    
    
def file_exists(file_path):
    """Check if a file already exists in the specified path."""
    return os.path.exists(file_path)
    
@csrf_exempt
def add_word(request):
    if request.method == 'POST':
        word = request.POST.get('word')
        difficulty = request.POST.get('difficulty')
        image = request.FILES.get('image')

        if not word or not difficulty or not image:
            return JsonResponse({'status': 'error', 'message': 'All fields are required!'})

     # Use the word as-is for naming the files
        file_safe_word = word.strip().lower()  # Strip whitespace for safety

        # Check if the image already exists
        image_name = f'{file_safe_word}'

        # Save the uploaded image to the specified folder
        fs = FileSystemStorage(location='media/images/')
        image_name = fs.save(f"{image_name}.jpg", image)

      #  image_name = fs.save(image.name, image)

        # Save the word and image path in the database
        Word.objects.create(
            word=word,
            difficulty=difficulty,
            image=f'images/{image_name}',
        )

        return JsonResponse({'status': 'success', 'message': 'Word added successfully!'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method!'})



from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Word
import logging



@csrf_exempt
def edit_word(request, word_id=None):
    """Add or edit a word, checking for existing image/audio."""
    if request.method == 'POST':
        # If word_id is provided, we are editing an existing word
        if word_id:
            word = get_object_or_404(Word, id=word_id)
        else:
            word = Word()  # If no word_id, it's a new word (creating)


        word_data = request.POST

        new_word = word_data.get('word', word.word)  # New word text from request

        # Handle audio deletion if the word changes
        if new_word != word.word:
            # Define the old audio file path
            old_audio_filename = f'{word.word.capitalize()}.mp3'
            old_audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', old_audio_filename)
            if os.path.exists(old_audio_path):
                os.remove(old_audio_path)  # Delete the old audio file


        word.word = word_data.get('word', word.word)
        word.difficulty = word_data.get('difficulty', word.difficulty)

        # Handle image upload
        if 'image' in request.FILES:
            image = request.FILES['image']
            image_path = os.path.join(settings.MEDIA_ROOT, 'images', image.name)

            if not file_exists(image_path):
                fs = FileSystemStorage(location='media/images/')
                image_name = fs.save(image.name, image)
                word.image = f'images/{image_name}'  # Save the new image path
            else:
                word.image = f'images/{image.name}'  # Use the existing image

        # Check and set the audio file path based on the word
        audio_filename = f'{word.word.capitalize()}.mp3'  # Capitalize the first letter of the word and add .mp3
        audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', audio_filename)

        if file_exists(audio_path):
            word.audio = f'audio/{audio_filename}'  # Use the existing audio

        word.save()  # Save the word to the database

        return JsonResponse({
            "status": "success",
            "message": "Word added/updated successfully",
            "word": word.word,
            "difficulty": word.difficulty,
            "image": word.image if word.image else "",
            "audio": word.audio if word.audio else ""
        })
    
    return JsonResponse({"status": "error", "message": "Invalid request method!"})


@csrf_exempt
def delete_word(request, word_id):
    try:
        word = get_object_or_404(Word, id=word_id)

        # Delete the image if it exists
        if word.image:
            image_path = os.path.join('media', word.image.path)  # Get the full path to the image
            if os.path.exists(image_path):
                os.remove(image_path)  # Delete the image from the file system

        # Delete the audio file
        audio_path = os.path.join('media', 'audio', f"{word.word.capitalize()}.mp3")
        if os.path.exists(audio_path):
            os.remove(audio_path)  # Delete the corresponding audio file

        word.delete()  # Delete the word record from the database

        return JsonResponse({
            "status": "success",
            "message": "Word and related files deleted successfully"
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        })
