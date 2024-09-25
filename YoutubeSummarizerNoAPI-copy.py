import os
import customtkinter
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import google.generativeai as genai
from PIL import Image, ImageTk
import requests
from io import BytesIO
from pytube import YouTube
import tkinter as tk

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

def startGemini(api_key):
    global model
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

def getApiKey():
    return os.getenv("OPENAI_API_KEY", "no api key set")

def getGeminiKey():
    return os.getenv("GEMINI_API_KEY", "no gemini api key set")

def getVideoID(video_url):
    if '?v=' in video_url:
        return video_url.split('?v=')[1].split('&')[0]
    elif 'live/' in video_url:
        return video_url.split('live/')[1].split('?')[0]
    elif 'youtu.be' in video_url:
        return video_url.split('be/')[1].split('?')[0]
    else:
        print('Not a recognized YouTube link')
        return video_url

def get_summary_chatgpt(prompt):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [{"role": "user", "content": prompt}]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="gpt-3.5-turbo",
    )
    return chat_completion.choices[0].message["content"]

def get_summary_gemini(prompt):
    response = model.generate_content(prompt)
    return response.text

# Custom tooltip class
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x800")
        self.title("Youtube Summarizer")

        self.language_var = customtkinter.StringVar(value="en")

        self.language_dropdown = customtkinter.CTkComboBox(
            self,
            values=["en"],  # Default language list
            variable=self.language_var,
            width=80
        )
        self.language_dropdown.grid(row=1, column=1, padx=20, pady=10)
        ToolTip(self.language_dropdown, text="Select the language of the transcript")

        self.summarizer_var = customtkinter.StringVar(value="Google Gemini")

        self.video_url_entry = customtkinter.CTkEntry(self, placeholder_text="Video URL", width=280)
        self.video_url_entry.grid(row=0, column=0, padx=20, pady=10)
        ToolTip(self.video_url_entry, text="Enter the YouTube video URL")

        # self.summarizer_dropdown = customtkinter.CTkComboBox(self, values=["ChatGPT", "Google Gemini", "SpaCy", "BERT"], variable=self.summarizer_var, width=280)
        self.summarizer_dropdown = customtkinter.CTkComboBox(self, values=["Google Gemini"], variable=self.summarizer_var, width=280)
        self.summarizer_dropdown.grid(row=1, column=0, padx=20, pady=10)
        self.summarizer_dropdown.bind("<<ComboboxSelected>>", self.on_summarizer_change)
        ToolTip(self.summarizer_dropdown, text="Select the summarization method")

        self.prompt_entry = customtkinter.CTkEntry(self, placeholder_text="Custom Prompt", width=450)
        self.prompt_entry.grid(row=2, column=0, columnspan=2, padx=20, pady=10)
        ToolTip(self.prompt_entry, text="Enter a custom prompt for summarization")

        self.api_key_entry = customtkinter.CTkEntry(self, show="*", placeholder_text="API Key", width=280)
        self.api_key_entry.grid(row=3, column=0, padx=20, pady=10)
        ToolTip(self.api_key_entry, text="Enter your API key")

        self.reveal_button = customtkinter.CTkButton(self, text="Reveal API Key", command=self.reveal_api_key)
        self.reveal_button.grid(row=3, column=1, padx=5, pady=10)
        ToolTip(self.reveal_button, text="Click to show or hide the API key")

        self.get_video_button = customtkinter.CTkButton(self, text="Get Video", command=self.get_video_info, width=100)
        self.get_video_button.grid(row=0, column=1, padx=20, pady=10)
        ToolTip(self.get_video_button, text="Retrieve video information and transcript")

        self.result_textbox = customtkinter.CTkTextbox(self, width=465, height=200, wrap="word")
        self.result_textbox.grid(row=4, column=0, columnspan=2, padx=20, pady=10)
        ToolTip(self.result_textbox, text="Displays the summarization result")

        self.submit_button = customtkinter.CTkButton(self, text="Submit", command=self.submit_click, width=280)
        self.submit_button.grid(row=5, column=0, padx=20, pady=10)
        ToolTip(self.submit_button, text="Submit the request for summarization")

        self.thumbnail_label = customtkinter.CTkLabel(self, text="")
        self.thumbnail_label.grid(row=6, column=0, columnspan=2, padx=20, pady=10)
        ToolTip(self.thumbnail_label, text="Displays the video thumbnail")

    def reveal_api_key(self):
        if self.api_key_entry.cget("show") == "":
            self.api_key_entry.configure(show="*")
        else:
            self.api_key_entry.configure(show="")

    def on_summarizer_change(self, event=None):
        summarizer = self.summarizer_var.get()
        if summarizer in ["ChatGPT", "Google Gemini"]:
            self.api_key_entry.grid(row=3, column=0, padx=20, pady=10)
            self.api_key_entry.configure(placeholder_text="API Key")
            self.reveal_button.grid(row=3, column=1, padx=5, pady=10)
        else:
            self.api_key_entry.grid_remove()
            self.reveal_button.grid_remove()

    def get_video_info(self):
        video_url = self.video_url_entry.get()
        video_id = getVideoID(video_url)
        
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            languages = [transcript.language_code for transcript in transcript_list]
            self.language_dropdown.configure(values=languages)
        except Exception as e:
            self.result_textbox.delete(1.0, "end")
            self.result_textbox.insert("end", f"Failed to retrieve transcript list: {e}")
            return

        try:
            yt = YouTube(video_url)
            thumbnail_url = yt.thumbnail_url
            response = requests.get(thumbnail_url)
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            img.thumbnail((500, 500))
            img = ImageTk.PhotoImage(img)
            self.thumbnail_label.configure(image=img)
            self.thumbnail_label.image = img  # Keep reference to avoid garbage collection
        except Exception as e:
            self.thumbnail_label.configure(text=f"Failed to load thumbnail: {e}")

    def submit_click(self):
        video_url = self.video_url_entry.get()
        api_key = self.api_key_entry.get()
        summarizer = self.summarizer_var.get()
        language = self.language_var.get()
        custom_prompt = self.prompt_entry.get()

        if summarizer == "Google Gemini":
            startGemini(api_key)

        video_id = getVideoID(video_url)

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        except Exception as e:
            self.result_textbox.delete(1.0, "end")
            self.result_textbox.insert("end", f"Failed to retrieve transcript: {e}")
            return

        transcript_word_list = ' '.join([t['text'] for t in transcript])
        final_prompt = f"{custom_prompt}\n{transcript_word_list}"

        if summarizer == "Google Gemini":
            summary = get_summary_gemini(final_prompt)


        self.result_textbox.delete(1.0, "end")
        self.result_textbox.insert("end", summary)

app = App()

def onPressExit():
    app.quit()

app.protocol("WM_DELETE_WINDOW", onPressExit)
app.mainloop()
