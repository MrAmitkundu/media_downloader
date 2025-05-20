from flask import Flask, request, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_choice = request.form.get('format')  # e.g., 'video' or 'audio'
    
    if not url:
        return "No URL provided", 400

    output_filename = f"download_{uuid.uuid4()}.%(ext)s"
ydl_opts = {
        'outtmpl': output_filename,
        'cookiefile': 'cookies.txt',  # <-- Add this line
}

    if format_choice == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        filename = ydl.prepare_filename(info)
        if format_choice == 'audio':
            filename = filename.rsplit('.', 1)[0] + '.mp3'
    
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # default to 5000 locally
    app.run(host='0.0.0.0', port=port)
