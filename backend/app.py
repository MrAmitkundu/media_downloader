from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import re
import io

app = Flask(__name__)
CORS(app)

progress_status = {'percent': 0, 'status': '', 'title': ''}

def sanitize_filename(name):
    return re.sub(r'[\/*?"<>|]', '', name)

@app.route('/')
def home():
    return 'Media Downloader Backend is running.'

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/progress')
def get_progress():
    return jsonify(progress_status)

@app.route('/download', methods=['POST'])
def download():
    global progress_status
    data = request.json
    url = data.get('url')
    media_type = data.get('type')  # 'video' or 'audio'
    quality = data.get('quality')

    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    platform = 'youtube' if 'youtube' in url or 'youtu.be' in url else 'facebook' if 'facebook.com' in url else 'unknown'

    try:
        progress_status = {'percent': 0, 'status': 'starting', 'title': ''}
        if platform == 'youtube':
            return download_youtube(url, media_type, quality)
        elif platform == 'facebook':
            return download_facebook(url, quality)
        else:
            return jsonify({'error': 'Unsupported platform'}), 400
    except Exception as e:
        progress_status = {'percent': 0, 'status': 'error', 'title': ''}
        return jsonify({'error': str(e)}), 500

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def progress_hook(d):
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0.0%').strip()
        percent_clean = strip_ansi(percent_str).replace('%', '')
        try:
            progress_status['percent'] = float(percent_clean)
        except ValueError:
            progress_status['percent'] = 0.0
        progress_status['status'] = 'downloading'
    elif d['status'] == 'finished':
        progress_status['percent'] = 100
        progress_status['status'] = 'finished'

def download_youtube(link, media_type, quality):
    global progress_status

    if media_type == 'video':
        format_str = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ext = 'mp4'
        postprocessors = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }]
    else:
        format_str = 'bestaudio/best'
        ext = 'mp3'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    output_buffer = io.BytesIO()
    temp_title = "temp_download"
    ydl_opts = {
        'format': format_str,
        'outtmpl': f'{temp_title}.%(ext)s',
        'cookiefile': 'cookies.txt',  # path to your cookies file included in repo
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'postprocessors': postprocessors or [],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        }

    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)
        title = sanitize_filename(info.get('title', 'media'))
        filename = f"{temp_title}.{ext}"
        final_filename = f"{title}_POIT_{media_type}.{ext}"

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            output_buffer.write(f.read())
        os.remove(filename)
        output_buffer.seek(0)

        progress_status['title'] = final_filename
        return send_file(
            output_buffer,
            as_attachment=True,
            download_name=final_filename,
            mimetype='application/octet-stream'
        )
    else:
        return jsonify({'error': 'File not found after processing'}), 500

def download_facebook(link, quality):
    global progress_status

    format_str = f"bestvideo[height={quality}]+bestaudio/best[height={quality}]/best"
    ext = 'mp4'
    temp_title = "fb_temp"
    output_buffer = io.BytesIO()

    ydl_opts = {
        'format': format_str,
        'outtmpl': f'{temp_title}.%(ext)s',
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)
        title = sanitize_filename(info.get('title', 'media'))
        filename = f"{temp_title}.{ext}"
        final_filename = f"{title}_POIT_video.{ext}"

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            output_buffer.write(f.read())
        os.remove(filename)
        output_buffer.seek(0)

        progress_status['title'] = final_filename
        return send_file(
            output_buffer,
            as_attachment=True,
            download_name=final_filename,
            mimetype='application/octet-stream'
        )
    else:
        return jsonify({'error': 'File not found after download'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
