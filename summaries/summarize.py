import os
import google.generativeai as genai
import speech_recognition as sr
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def upload_file_with_retry(client, file_path):
    try:
        return client.files.upload(file=file_path)
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        raise

def analyze_local_audio(file_path, api_key):
    """
    Analyze the local audio file and return a summary string.
    Only supports WAV/AIFF/FLAC (no MP3).
    """
    logger.debug(f"Attempting to analyze audio file at: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at: {file_path}")

    if not api_key:
        placeholder = (
            f"Placeholder summary for file {os.path.basename(file_path)}\n"
            "(No GEMINI_API_KEY set — this is a local stub.)\n\n"
            "Decisions:\n- None detected (placeholder)\n\n"
            "Action Items:\n- No action items (placeholder)\n\n"
            "Unresolved Questions:\n- No unresolved questions (placeholder)\n"
        )
        return placeholder

    try:
        # Recognize speech
        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Could not understand audio."
        except sr.RequestError as e:
            return f"Speech recognition API error: {str(e)}"

        # Summarize with Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Please provide a concise summary of this meeting transcript:\n\n{text}"
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.exception("Error during audio analysis")
        raise

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Summarize a WAV/FLAC/AIFF audio file using Google Gemini.")
    parser.add_argument("--file", required=True, help="Path to the audio file (must be WAV/FLAC/AIFF).")
    parser.add_argument("--apikey", required=False, help="Google Gemini API key (or set GEMINI_API_KEY env var).")
    args = parser.parse_args()

    api_key = args.apikey or os.getenv("GEMINI_API_KEY", "")
    
    try:
        summary = analyze_local_audio(args.file, api_key)
        print("\n--- SUMMARY ---\n")
        print(summary)
    except Exception as e:
        logger.error(f"Failed to process audio: {e}")
        exit(1)
