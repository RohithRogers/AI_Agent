import os
import sys
import json
import queue
import pyaudio
import vosk
from vosk import Model, KaldiRecognizer
from tools.registry import tool
from rich.console import Console

# Suppress Vosk logging
vosk.SetLogLevel(-1)

# Global cache for the model to speed up subsequent calls
_model_cache = {}

class VoiceTranscriber:
    def __init__(self, model):
        self.model = model
        self.q = queue.Queue()

    def callback(self, in_data, frame_count, time_info, status):
        self.q.put(in_data)
        return (None, pyaudio.paContinue)

    def transcribe(self, timeout=None):
        """
        Listens to the microphone and returns the first recognized sentence.
        """
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=8000,
                        stream_callback=self.callback)

        rec = KaldiRecognizer(self.model, 16000)
        
        recognized_text = ""
        try:
            stream.start_stream()
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    recognized_text = res.get("text", "")
                    if recognized_text:
                        break
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        return recognized_text

@tool("get_voice_input", "Listens to the microphone and transcribes speech to text using Vosk.", {})
def get_voice_input(model_path="vosk-model-small-en-us-0.15"):
    global _model_cache
    console = Console()

    if model_path not in _model_cache:
        if not os.path.exists(model_path):
            return "Error: Voice model directory not found."
        
        # Optionally show loading status
        # with console.status("[bold cyan]Loading Voice Model...[/bold cyan]"):
        _model_cache[model_path] = Model(model_path)
    
    transcriber = VoiceTranscriber(_model_cache[model_path])
    
    # Only print this when ready
    console.print("[bold yellow]🎤 Listening... (Speak now)[/bold yellow]")
    
    return transcriber.transcribe()
