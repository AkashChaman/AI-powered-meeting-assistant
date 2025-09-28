from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pathlib
import importlib.util
import sys
import traceback
import logging

# Import google.generativeai with error handling
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google.generativeai not available. Install with: pip install google-generativeai")

# Import dotenv with error handling
try:
    import dotenv
    dotenv.load_dotenv()  # Load environment variables from .env file if present
except ImportError:
    print("Warning: python-dotenv not available. Install with: pip install python-dotenv")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads')
SUMMARIES_FOLDER = os.path.join(APP_ROOT, 'summaries')
FRONTEND_FOLDER = os.path.join(APP_ROOT, 'frontend')

# Create required directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARIES_FOLDER, exist_ok=True)
os.makedirs(FRONTEND_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_FOLDER, template_folder=FRONTEND_FOLDER)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'avi', 'mov', 'mkv', 'm4a', 'flac', 'aac'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# Serve assets under /home/ path (maps to frontend/home/)
@app.route('/home/<path:filename>')
def frontend_home_assets(filename):
    home_path = os.path.join(FRONTEND_FOLDER, 'home')
    if not os.path.exists(home_path):
        return jsonify({'error': 'Home directory not found'}), 404
    return send_from_directory(home_path, filename)

@app.route('/')
def index():
    """Serve the main page."""
    summarizer_html = os.path.join(FRONTEND_FOLDER, 'summarizer.html')
    if os.path.exists(summarizer_html):
        return send_from_directory(FRONTEND_FOLDER, 'summarizer.html')
    else:
        # Return a simple HTML page if summarizer.html doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Audio Summarizer</title>
        </head>
        <body>
            <h1>Audio Summarizer</h1>
            <p>Upload an audio file to get started.</p>
            <form action="/upload-and-summarize" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept="audio/*,video/*" required>
                <button type="submit">Upload and Summarize</button>
            </form>
        </body>
        </html>
        '''

@app.route('/upload-and-summarize', methods=['POST'])
def upload_and_summarize():
    """Handle file upload and summarization."""
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400

        file = request.files['file']
        if file.filename == '' or file.filename is None:
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Supported formats: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Secure the filename and save file
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
            
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        logger.info(f"File saved to: {save_path}")

        # Check for API key
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'GEMINI_API_KEY environment variable not set'}), 500

        # Check for required packages
        try:
            import google.generativeai as genai
        except ImportError:
            return jsonify({'error': 'google-generativeai package not installed. Install with: pip install google-generativeai'}), 500

        # Import and use the summarizer
        summary = None
        try:
            summarizer_path = os.path.join(APP_ROOT, 'app', 'summarizer.py')
            if not os.path.exists(summarizer_path):
                return jsonify({'error': 'Summarizer module not found at app/summarizer.py'}), 500
                
            spec = importlib.util.spec_from_file_location('local_summarizer', summarizer_path)
            if spec is None or spec.loader is None:
                return jsonify({'error': 'Failed to load summarizer module spec'}), 500
                
            summarizer_module = importlib.util.module_from_spec(spec)
            sys.modules['local_summarizer'] = summarizer_module
            spec.loader.exec_module(summarizer_module)
            
            if not hasattr(summarizer_module, 'analyze_local_audio'):
                return jsonify({'error': 'analyze_local_audio function not found in summarizer module'}), 500
                
            analyze_local_audio = getattr(summarizer_module, 'analyze_local_audio')
            summary = analyze_local_audio(save_path, api_key)
            
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            tb = traceback.format_exc()
            summary = f'Error during analysis: {str(e)}\n\nTraceback:\n{tb}'

        # Save summary to timestamped file
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        summary_filename = f'summary_{timestamp}.txt'
        summary_path = os.path.join(SUMMARIES_FOLDER, summary_filename)
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as fh:
                fh.write(summary or 'No summary generated.')
            logger.info(f"Summary saved to: {summary_path}")
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            return jsonify({'error': f'Failed to save summary file: {str(e)}'}), 500

        # Clean up uploaded file (optional)
        try:
            os.remove(save_path)
            logger.info(f"Cleaned up uploaded file: {save_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up uploaded file: {e}")

        download_url = f'/download-summary/{summary_filename}'
        return jsonify({
            'summary': summary,
            'download_url': download_url,
            'filename': summary_filename
        })

    except Exception as e:
        logger.error(f"Unexpected error in upload_and_summarize: {e}")
        tb = traceback.format_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}', 'traceback': tb}), 500

@app.route('/download-summary/<path:filename>')
def download_summary(filename):
    """Serve the saved summary file for download."""
    try:
        # Validate filename for security
        safe_filename = secure_filename(filename)
        if not safe_filename or safe_filename != filename:
            return jsonify({'error': 'Invalid filename'}), 400
            
        summary_path = os.path.join(SUMMARIES_FOLDER, safe_filename)
        if not os.path.exists(summary_path):
            return jsonify({'error': 'Summary file not found'}), 404
            
        return send_from_directory(SUMMARIES_FOLDER, safe_filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading summary: {e}")
        return jsonify({'error': 'Failed to download summary'}), 500

@app.route('/save-summary', methods=['POST'])
def save_summary():
    """Save a manually provided summary."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        summary = data.get('summary', '')
        if not summary or not summary.strip():
            return jsonify({'error': 'No summary content provided'}), 400

        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        summary_filename = f'summary_manual_{timestamp}.txt'
        summary_path = os.path.join(SUMMARIES_FOLDER, summary_filename)
        
        with open(summary_path, 'w', encoding='utf-8') as fh:
            fh.write(summary.strip())
            
        logger.info(f"Manual summary saved to: {summary_path}")
        return jsonify({
            'ok': True,
            'filename': summary_filename,
            'download_url': f'/download-summary/{summary_filename}'
        })

    except Exception as e:
        logger.error(f"Error saving manual summary: {e}")
        return jsonify({'error': f'Failed to save summary: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'genai_available': GENAI_AVAILABLE,
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    # Validate required environment variables
    if not os.environ.get('GEMINI_API_KEY'):
        print("Warning: GEMINI_API_KEY environment variable not set")
    
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Summaries folder: {SUMMARIES_FOLDER}")
    print(f"Frontend folder: {FRONTEND_FOLDER}")
    
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)