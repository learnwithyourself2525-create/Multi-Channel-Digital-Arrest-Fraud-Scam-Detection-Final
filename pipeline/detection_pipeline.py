from models.text_classifier import TextClassifier
from models.audio_processor import AudioProcessor
from models.video_deepfake_detector import VideoDeepfakeDetector
import numpy as np
import cv2
from moviepy.editor import VideoFileClip
import os
import asyncio

# --- 1. MODEL INITIALIZATION (No changes here) ---
try:
    text_classifier = TextClassifier()
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize TextClassifier: {e}")
    text_classifier = None
try:
    audio_processor = AudioProcessor()
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize AudioProcessor: {e}")
    audio_processor = None
try:
    video_detector = VideoDeepfakeDetector()
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize VideoDeepfakeDetector: {e}")
    video_detector = None

# --- 2. UPDATED ASYNC PROCESSING FUNCTIONS ---

async def process_text_input(text: str) -> dict:
    """Runs the text model in a background thread to avoid blocking."""
    if not text_classifier:
        return {"type": "text_analysis", "result": {"error": "Text model not available."}}
    # Use asyncio.to_thread to run the synchronous, blocking function
    prediction = await asyncio.to_thread(text_classifier.predict, text)
    return {"type": "text_analysis", "result": prediction}

async def process_audio_input(audio_path: str) -> dict:
    """Runs the audio and text models in background threads."""
    if not audio_processor or not text_classifier:
        return {"type": "audio_analysis", "result": {"error": "Audio/Text model not available."}}

    # Run the blocking audio processing in a thread
    audio_result = await asyncio.to_thread(audio_processor.process_audio, audio_path)
    if "error" in audio_result:
        return {"type": "audio_analysis", "result": audio_result}

    transcribed_text = audio_result.get("transcribed_text", "")
    # Run the subsequent text prediction in a thread
    text_prediction = await asyncio.to_thread(text_classifier.predict, transcribed_text)
    
    return {
        "type": "audio_analysis",
        "result": {
            "transcription": transcribed_text,
            "scam_analysis": text_prediction
        }
    }

def process_video_frame(frame_bytes: bytes) -> dict:
    """
    Processes a single video frame. This remains synchronous because it's
    called by the non-async WebSocket handler for the live feed.
    """
    if not video_detector:
        return {"type": "video_analysis", "result": {"error": "Video model not available."}}

    np_arr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"type": "video_analysis", "result": {"face_detected": False, "error": "Invalid frame"}}

    # This is a blocking call, which might make the live feed a bit choppy,
    # but is necessary for the current structure.
    deepfake_result = video_detector.analyze_frame(frame)
    return {"type": "video_analysis", "result": deepfake_result}

async def process_video_file(video_path: str, manager) -> dict:
    """
    Processes a full video file, sending status updates and running
    blocking operations in background threads.
    """
    try:
        await manager.broadcast({"type": "status_update", "message": "Video analysis started..."})

        # --- Audio Extraction and Analysis ---
        await manager.broadcast({"type": "status_update", "message": "Extracting audio from video..."})
        temp_audio_path = "temp_extracted_audio.mp3"
        
        def extract_audio():
            """Wrapper for the blocking moviepy call."""
            with VideoFileClip(video_path) as video_clip:
                if video_clip.audio:
                    video_clip.audio.write_audiofile(temp_audio_path, codec='mp3', logger=None)
                    return True
            return False

        has_audio = await asyncio.to_thread(extract_audio)
        
        if has_audio:
            await manager.broadcast({"type": "status_update", "message": "Analyzing extracted audio..."})
            audio_analysis_result = await process_audio_input(temp_audio_path)
            os.remove(temp_audio_path)
        else:
            audio_analysis_result = {"type": "audio_analysis", "result": {"error": "No audio track found."}}

        # --- Video Frame Analysis ---
        await manager.broadcast({"type": "status_update", "message": "Analyzing a sample video frame..."})

        def analyze_frame_from_file():
            """Wrapper for blocking OpenCV and DeepFace calls."""
            vidcap = cv2.VideoCapture(video_path)
            success, frame = vidcap.read()
            vidcap.release()
            if success:
                _, frame_bytes = cv2.imencode('.jpg', frame)
                return process_video_frame(frame_bytes.tobytes())
            return {"type": "video_analysis", "result": {"face_detected": False, "error": "Could not read frame."}}

        frame_analysis_result = await asyncio.to_thread(analyze_frame_from_file)
        
        await manager.broadcast({"type": "status_update", "message": "Analysis complete!"})

        # --- Final Combination ---
        final_result = {
            "video_file_analysis": {
                "audio_component": audio_analysis_result.get("result", {}),
                "video_component": frame_analysis_result.get("result", {})
            }
        }
        await manager.broadcast({"type": "video_file_analysis", "result": final_result["video_file_analysis"]})
        return final_result

    except Exception as e:
        error_message = f"An unexpected error occurred during video processing: {str(e)}"
        await manager.broadcast({"type": "status_update", "message": error_message})
        return {"error": error_message}