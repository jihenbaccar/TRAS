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




"""
def pronunciation_view(request):
    word = "Cat"  # Example word
    image_name = "cat.jpg"  # Example image file name

    # Construct the full path for the image
    image_path = os.path.join(settings.MEDIA_ROOT, 'images', image_name)

    # Check if the image exists
    if os.path.exists(image_path):
        image_url = f"/media/images/{image_name}"
    else:
        image_url = "/media/images/default.jpg"  # Fallback image if not found

    return render(request, 'pronunciation.html', {'word': word, 'image_url': image_url})

"""

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
'''
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    pages_text = []
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text = page.get_text("text")
        pages_text.append(text)
    return pages_text

from gtts import gTTS
import os

def generate_audio(text, filename="output.mp3"):
    tts = gTTS(text, lang='en')
    tts.save(filename)
    return filename


def generate_audio_for_story(pdf_path):
    pages_text = extract_text_from_pdf(pdf_path)
    audio_files = []
    for i, text in enumerate(pages_text):
        audio_filename = f"story_page_{i+1}.mp3"
        generate_audio(text, audio_filename)
        audio_files.append(audio_filename)
    return audio_files



from django.http import HttpResponse
from django.conf import settings
import os

def serve_audio(request, filename):
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'stories', filename)
    if os.path.exists(audio_file_path):
        with open(audio_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type="audio/mpeg")
            response['Content-Disposition'] = f'inline; filename={filename}'
            return response
    return HttpResponse(status=404)


from django.shortcuts import render

def story_detail(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    return render(request, 'story_detail.html', {
        'story': story,
    })

def story_view(request):
    story = get_object_or_404(Story, pk=story_id)  # Assuming you retrieve the story from the database
    return render(request, 'story_detail.html', {'story': story})


    
    '''

import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from gtts import gTTS
import fitz  # PyMuPDF
from .models import Story

from PIL import Image
import pytesseract
import io


'''
def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    return [page.get_text("text") for page in document]
    '''

'''
def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    pages_text = []
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    for page_num in range(len(document)):
        page = document.load_page(page_num)
        
        # Extract the page as an image
        pix = page.get_pixmap()  # Create a pixmap (image) of the page
        img = Image.open(io.BytesIO(pix.tobytes()))  # Open the image with Pillow

        # Use pytesseract to perform OCR on the image and extract text
        text = pytesseract.image_to_string(img)

        if not text.strip():  # Handle empty text
            print(f"No text found on page {page_num}")
        else:
            pages_text.append(text)  # Only append non-empty text
    
    return pages_text
'''

def generate_audio_for_story(story):
    audio_files = []
    pages_text = extract_text_from_pdf(story.pdf.path)
    for i, text in enumerate(pages_text):
        audio_filename = f"story_{story.id}_page_{i+1}.mp3"
        audio_path = os.path.join('media/stories/audio', audio_filename)
        tts = gTTS(text, lang='en')
        tts.save(audio_path)
        audio_files.append(audio_filename)
    story.audio_files = audio_files
    story.save()

'''
def story_detail(request, story_id):
    # Fetch the story object
    story = get_object_or_404(Story, pk=story_id)

    # Construct the full URL for the PDF
    pdf_url = settings.MEDIA_URL + str(story.pdf)

    # Render the HTML template with the story data and PDF URL
    return render(request, 'story_detail.html', {'story': story, 'pdf_url': pdf_url})
'''

def story_detail(request, story_id):
    # Fetch the story object
    story = get_object_or_404(Story, pk=story_id)

    # If the story does not have audio files, regenerate them
    if not story.audio_files:
        generate_audio_for_story(story)

    # Construct the full URL for the PDF
    pdf_url = settings.MEDIA_URL + str(story.pdf)
    audio_files = story.audio_files  # Get the audio files from the database

    # Render the HTML template with the story data and PDF URL
    return render(request, 'story_detail.html', {'story': story, 'pdf_url': pdf_url, 'audio_files': audio_files})





def check_answer(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    question_index = int(request.GET.get('question_index'))
    user_answer = request.GET.get('answer')
    correct_answer = story.questions[question_index]["correct_answer"]
    return JsonResponse({'result': user_answer == correct_answer})



from django.http import HttpResponse
from django.conf import settings
import os
import re


def serve_audio(request, filename):
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'stories', filename)
    if os.path.exists(audio_file_path):
        with open(audio_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type="audio/mpeg")
            response['Content-Disposition'] = f'inline; filename={filename}'
            return response




# Preprocess the image for OCR
def preprocess_image(image):
    # Convert image to grayscale
    gray_image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)

    # Apply binary thresholding
    _, thresh_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY)

    # Optional: Apply median blur to remove noise
    processed_image = cv2.medianBlur(thresh_image, 3)

    return processed_image

def filter_text(text):
    filtered_text = []
    for line in text.splitlines():
        # Skip lines that look like code comments or contain URLs
        if not re.match(r'^\s*//.*$', line) and not re.match(r'.*//.*$', line):  # Remove // comments
            if re.match(r'https?://[^\s]+', line):  # Skip URLs
                continue
            filtered_text.append(line)
    return "\n".join(filtered_text)

# Updated text extraction function with filtering
def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    pages_text = []

    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    for page_num in range(len(document)):
        page = document.load_page(page_num)

        # Extract the page as an image
        pix = page.get_pixmap()  # Create a pixmap (image) of the page
        img = Image.open(io.BytesIO(pix.tobytes()))  # Open the image with Pillow

        # Preprocess the image before passing to Tesseract
        processed_img = preprocess_image(img)

        # Use pytesseract to perform OCR on the processed image and extract text
        text = pytesseract.image_to_string(processed_img, config='--psm 6')

        if text.strip():  # Only process non-empty text
            filtered_text = filter_text(text)  # Filter out unwanted lines
            pages_text.append(filtered_text)  # Append the filtered text

    return pages_text