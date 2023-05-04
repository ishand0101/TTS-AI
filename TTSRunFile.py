"""
Text-to-Speech Translator

The Text-to-Speech Translator is a Python application that allows users to convert text or PDF files to audio files in a variety of languages.
The application uses the gTTS library for text-to-speech conversion and the OpenAI API for language translation. 
Users can select their desired target language and the application will automatically translate the text before converting it to speech.
The application includes sentiment analysis functionality to automatically adjust the speed of the generated speech based on the sentiment of the translated text. 
This affects playback speed of the voice in the audio file.
The application also includes an audio player with basic controls for opening, playing, and stopping audio files. 
The application also includes a recent files list, allowing users to quickly access previously opened audio files.

Author: Ishan Deva
"""
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import tkinter.font as tkFont   
from ttkthemes import ThemedTk
from gtts import gTTS
import PyPDF2
import openai
import os
import tempfile
import threading
import pygame
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")
pygame.mixer.init()
#TRANSLATION FEATURE START

def translate_text(text, target_language):
    translated_text = ""
    max_token_length = 2048  # Maximum token length for the API
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk + line) < max_token_length:
            current_chunk += line + "\n"
        else:
            # translate current chunk
            response = None
            while response is None:
                try:
                    response = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=f"Translate the following English text to {target_language}:\n\n{current_chunk}. If the target language is in the same language that the text is in, do not change the text and simply return it as it is. Only translate the text after the target language and colon if the languages are not the same. This output text is to be fed into gTTS library, which requires the text to be in easy to manage output. Please account for this.",
                        temperature=0.8,
                        max_tokens=2048, 
                    )
                    translated_text += response.choices[0].text.strip() + "\n"
                    current_chunk = line + "\n"
                except openai.error.RateLimitError:
                    print("Rate limited. Waiting 3 seconds before retrying...")
                    time.sleep(3)
            time.sleep(0.5)

    # translate last chunk
    response = None
    while response is None:
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Translate the following English text to {target_language}:\n\n{current_chunk}. If the target language is in the same language that the text is in, do not change the text and simply return it as it is. Only translate the text after the target language and colon if the languages are not the same. This output text is to be fed into gTTS library, which requires the text to be in easy to manage output. Please account for this.",
                temperature=0.8,
                max_tokens=2048, 
            )
            translated_text += response.choices[0].text.strip()
        except openai.error.RateLimitError:
            print("Rate limited. Waiting 3 seconds before retrying...")
            time.sleep(3)
        time.sleep(0.5)

    # Check if the selected target language is a valid language code. If it's not, default to English. To avoid no-lang errors.
    if target_language not in language_codes:
        target_language = "English"

    return translated_text
pdf_text = ""
def text_to_speech():
    global pdf_text, recent_files

    # Get the text input from the UI
    text = text_input.get() or pdf_text
    print(f"Text before translation: {text}")
    target_language = language_var.get()
    
    if text.strip():
        # Translate the text
        translated_text = translate_text(text, target_language)
        print(f"Text after translation: {translated_text}")

        if target_language == "English":
            sentiment = get_sentiment(translated_text)
            if sentiment == "positive":
                tts_speed = 0.9
            elif sentiment == "negative":
                tts_speed = 1.1
            else:
                tts_speed = 1.0
        else:
            tts_speed = 1.0

        # Break the text into smaller chunks
        text_chunks = translated_text.split('\n')

        # Create a temporary directory to store the audio chunks
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_chunks = []
            for idx, chunk in enumerate(text_chunks):
                if chunk.strip():
                    # Convert translated text chunk to speech
                    tts = gTTS(text=chunk.strip(), lang=language_codes[target_language], slow=False)
                    tts.speed = tts_speed
                    # Save the audio chunk in the temporary directory
                    chunk_path = os.path.join(temp_dir, f"audio_chunk_{idx}.mp3")
                    tts.save(chunk_path)
                    audio_chunks.append(chunk_path)

            # Ask the user for a file save location
            file_path = filedialog.asksaveasfilename(defaultextension='.mp3')

            # Save the audio file to the chosen location
            if file_path:
                # Combine the audio chunks into a single file
                with open(file_path, 'wb') as output_file:
                    for chunk_path in audio_chunks:
                        with open(chunk_path, 'rb') as chunk_file:
                            output_file.write(chunk_file.read())

                # Add the selected file path to the recent files list
                recent_files.append(file_path)
                # Update the recent files listbox
                recent_files_listbox.delete(0, END)
                for file_path in recent_files:
                    recent_files_listbox.insert(END, file_path)
            
def select_pdf_file():
    global pdf_text, recent_files

    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()

        pdf_text = text
        print(f"Extracted text from PDF: {pdf_text}")

        text_input.delete(0, END)
        text_input.insert(INSERT, pdf_text)

def text_to_speech_thread():
    global progress_bar
    progress_bar.grid() 
    progress_bar.start(100)  
    text_to_speech()
    progress_bar.stop()  
    progress_bar.grid_remove() 

#why? progress bar thread and tts thread crashed app
def start_text_to_speech_thread(event):
    global text_to_speech_thread_obj
    text_to_speech_thread_obj = threading.Thread(target=text_to_speech_thread)
    text_to_speech_thread_obj.start()

language_codes = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Hindi": "hi",
    "Greek": "el",
    "Swedish": "sv",
    "Polish": "pl",
}

#TRANSLATE FEATURE END

#AUDIO PLAYER FEATURE START

audio_file_path = None
audio_paused = False
def play_audio():
    if audio_file_path: 
        pygame.mixer.music.play()

def stop_audio():
    pygame.mixer.music.stop()

def open_audio_file():
    global audio_file_path, recent_files

    audio_file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
    if audio_file_path:
        stop_audio()
        pygame.mixer.music.load(audio_file_path)
        play_audio()
        if audio_file_path not in recent_files:
            recent_files.append(audio_file_path)
            recent_files_listbox.insert(END, audio_file_path)
#AUDIO FEATURE END 

#RECENT AUDIO FILES FEATURE START
recent_files = []
def open_recent_file(file_path):
    global audio_file_path
    audio_file_path = file_path
    stop_audio()
    pygame.mixer.music.load(audio_file_path)
    play_audio()
#RECENT AUDIO FILES FEATURE END

#VOICE FEATURE START
#VOICE FEATURE END 

#UI START
root = ThemedTk(theme="equilux")
root.title("Text-to-Speech Translator")
root.minsize(800, 600) 
root.iconbitmap('C:\\Users\\Ishan\\Desktop\\TextToSpeech\\image.ico')

frame = ttk.Frame(root, padding="10")
frame.pack(fill=BOTH, expand=True)

#CUSTOM FONTS START
default_font = tkFont.nametofont("TkDefaultFont")
default_font.configure(size=16)  
frame.option_add("*Font", default_font)
style = ttk.Style()
style.configure("Custom.TButton", background="#007FFF", foreground="white") 
style.map("Custom.TButton",
          background=[("active", "#0059b3"), ("disabled", "#b3b3b3")],
          foreground=[("disabled", "#b3b3b3")])
style.configure("Custom.TMenubutton", background="#007FFF", foreground="white") 
style.map("Custom.TMenubutton",
          background=[("active", "#0059b3"), ("disabled", "#b3b3b3")],
          foreground=[("disabled", "#b3b3b3")])
style.configure("Custom.TMenubutton.Border",
                relief="raised",
                borderwidth=4,
                background="#007FFF")
#CUSTOM FONTS END


text_label = ttk.Label(frame, text="Enter text:", foreground="white")
text_label.grid(row=0, column=0, sticky=W, pady=(0, 10))
text_input = ttk.Entry(frame, font=("Arial", 20), width=50)
text_input.grid(row=1, column=0, sticky=W, padx=(0, 10))
pdf_button = ttk.Button(frame, text="Select PDF file", command=select_pdf_file, style="Custom.TButton")
pdf_button.grid(row=1, column=1, sticky=W)

language_label = ttk.Label(frame, text="Select target language:", foreground="white")
language_label.grid(row=2, column=0, sticky=W, pady=(10, 0))

language_var = StringVar(root)
language_var.set("English")  #default language
language_dropdown = ttk.OptionMenu(frame, language_var, "English", *list(language_codes.keys()), style="Custom.TMenubutton")
language_dropdown.grid(row=3, column=0, sticky=W)
language_dropdown = ttk.OptionMenu(frame, language_var, "English", *list(language_codes.keys()), style="Custom.TMenubutton")
language_dropdown.grid(row=3, column=0, sticky=W)

progress_bar = ttk.Progressbar(frame, mode='indeterminate', value=0, length=800)
progress_bar.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky=(W, E))
progress_bar.grid_remove()  # Hide the progress bar initially

text_to_speech_button = ttk.Button(frame, text="Convert text to Audio File", style="Custom.TButton")
text_to_speech_button.bind("<Button-1>", start_text_to_speech_thread)
text_to_speech_button.grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky=(W, E))


# def open_audio_file():
#     global audio_file_path, recent_files

#     audio_file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
#     if audio_file_path:
#         stop_audio()
#         pygame.mixer.music.load(audio_file_path)
#         play_audio()

#         # Add the selected file path to the recent files list
#         if audio_file_path not in recent_files:
#             recent_files.append(audio_file_path)
#             recent_files_listbox.insert(END, audio_file_path)
#garbage code
#AUDIO BUTTONS
audio_buttons_frame = ttk.Frame(frame)
audio_buttons_frame.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky=(W, E))

open_audio_button = ttk.Button(audio_buttons_frame, text="Open", command=open_audio_file, style="Custom.TButton")
open_audio_button.pack(side=LEFT, padx=(0, 10))

play_audio_button = ttk.Button(audio_buttons_frame, text="Play", command=play_audio, style="Custom.TButton")
play_audio_button.pack(side=LEFT, padx=(0, 10))

stop_audio_button = ttk.Button(audio_buttons_frame, text="Stop", command=stop_audio, style="Custom.TButton")
stop_audio_button.pack(side=LEFT, padx=(0, 10))
#AUDIO BUTTONS END

#RECENT AUDIO FILES SPACE
recent_files_frame = ttk.Frame(frame, padding="10")
recent_files_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky=(W, E))
recent_files_label = ttk.Label(recent_files_frame, text="Recently opened files:", foreground="white")
recent_files_label.pack(side=TOP, anchor=W)
recent_files_listbox = Listbox(recent_files_frame, font=("Arial", 12), width=50)
recent_files_listbox.pack(side=LEFT, fill=BOTH, expand=True)
for file_path in recent_files:
    recent_files_listbox.insert(END, file_path)
def recent_files_listbox_select(event):
    selection_index = recent_files_listbox.curselection()
    if selection_index:
        selection = recent_files_listbox.get(selection_index[0])
        open_recent_file(selection)
recent_files_listbox.bind("<<ListboxSelect>>", recent_files_listbox_select)
#RECENT AUDIO FILES SPACE END

#SENTIMENT ANALYSIS SECTION START
def get_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(text)
    compound_score = sentiment_score['compound']
    
    if compound_score >= 0.05:
        sentiment = "positive"
    elif compound_score <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"
        print(f'Sentiment Value: {sentiment}')
    return sentiment
#SENTIMENT ANALYSIS SECTION END

root.mainloop()