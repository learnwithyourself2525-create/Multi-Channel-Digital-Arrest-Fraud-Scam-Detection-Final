# In models/audio_processor.py

import whisper
import os
import soundfile as sf
import librosa
import numpy as np

class AudioProcessor:
    def __init__(self):
        # This still loads the whisper model, which is fine.
        # The issue is with the transcription backend, which we will bypass.
        self.model = whisper.load_model("small")

    def process_audio(self, audio_path: str):
        if not os.path.exists(audio_path):
            return {"error": "Audio file not found."}
        try:
            # --- NEW CODE ---
            # 1. Load the audio file using soundfile
            audio_data, sample_rate = sf.read(audio_path)

            # 2. Ensure audio is mono
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)

            # 3. Resample to 16kHz, which Whisper requires
            if sample_rate != 16000:
                audio_data = librosa.resample(y=audio_data, orig_sr=sample_rate, target_sr=16000)

            # 4. Convert to float32, which is the expected format
            audio_data = audio_data.astype(np.float32)
            
            # --- END NEW CODE ---
            
            # Transcribe the audio data directly from the numpy array
            result = self.model.transcribe(audio_data, fp16=False)
            transcribed_text = result["text"]
            
            return {"transcribed_text": transcribed_text}
            
        except Exception as e:
            return {"error": f"Failed to process audio: {str(e)}"}