
import os
import uuid
import threading
import subprocess
import re
import ffmpeg
from flask import Flask, request, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi'}

app = Flask(__name__, static_folder='web', static_url_path='/')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

progress = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_duration(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except Exception:
        return None

def convert_file(file_id, input_path, output_path):
    total_duration = get_duration(input_path)
    progress[file_id] = 0.0

    cmd = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', output_path
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')

    for line in process.stdout:
        match = time_pattern.search(line)
        if match and total_duration:
            hours, minutes, seconds = map(float, match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds
            percent = min(100.0, (current_time / total_duration) * 100)
            progress[file_id] = round(percent, 2)

    progress[file_id] = 100.0

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    format = request.form.get('format')

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    if format not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Invalid format'}), 400

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
    file.save(input_path)

    output_filename = f"{file_id}.{format}"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    progress[file_id] = 0

    threading.Thread(target=convert_file, args=(file_id, input_path, output_path)).start()

    return jsonify({'file_id': file_id, 'output': output_filename})

@app.route('/progress/<file_id>', methods=['GET'])
def get_progress(file_id):
    return jsonify({'progress': progress.get(file_id, 0.0)})

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
