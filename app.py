import os
import subprocess
import logging
from urllib.parse import quote
from flask import Flask, request, jsonify, Response, stream_with_context, render_template
import yt_dlp

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # On Windows local dev, use the ffmpeg.exe in the root folder. On Linux (Docker/Render) use system ffmpeg.
    ffmpeg_loc = os.path.join(app.root_path, 'ffmpeg.exe')
    if not os.path.exists(ffmpeg_loc):
        ffmpeg_loc = 'ffmpeg' # Use system PATH

    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['web', 'default']}},
        'ffmpeg_location': ffmpeg_loc
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            extractor = info.get('extractor_key', 'Unknown')
            
            return jsonify({
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'extractor': extractor
            })
    except Exception as e:
        app.logger.error(f"Error fetching info: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['GET'])
def download():
    url = request.args.get('url')
    media_type = request.args.get('type', 'video') 
    quality = request.args.get('quality', 'high') 
    
    if not url:
        return "URL required", 400
        
    is_audio = (media_type == 'audio')
    format_str = 'best'
    if is_audio:
        format_str = 'bestaudio/best'
    else:
        if quality == 'low':
            format_str = 'bestvideo[height<=480]+bestaudio/best'
        elif quality == 'medium':
            format_str = 'bestvideo[height<=720]+bestaudio/best'
        elif quality == 'high':
            format_str = 'bestvideo[height<=1080]+bestaudio/best'
        else:
            format_str = 'bestvideo+bestaudio/best'

    # On Windows local dev, use the ffmpeg.exe in the root folder. On Linux (Docker/Render) use system ffmpeg.
    ffmpeg_loc = os.path.join(app.root_path, 'ffmpeg.exe')
    if not os.path.exists(ffmpeg_loc):
        ffmpeg_loc = 'ffmpeg' # Use system PATH

    ydl_opts = {
        'format': format_str,
        'quiet': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['web', 'default']}},
        'ffmpeg_location': ffmpeg_loc
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'download')
            
            stream_urls = []
            if 'requested_formats' in info:
                stream_urls = [f['url'] for f in info['requested_formats']]
            else:
                stream_urls = [info['url']]


            
            if is_audio:
                cmd = [ffmpeg_loc, '-i', stream_urls[0], '-q:a', '2', '-f', 'mp3', 'pipe:1']
                filename = f"{title}.mp3"
                mimetype = "audio/mpeg"
            else:
                if len(stream_urls) == 2:
                    cmd = [ffmpeg_loc, '-i', stream_urls[0], '-i', stream_urls[1], '-c', 'copy', '-f', 'mp4', '-movflags', 'frag_keyframe+empty_moov', 'pipe:1']
                else:
                    cmd = [ffmpeg_loc, '-i', stream_urls[0], '-c', 'copy', '-f', 'mp4', '-movflags', 'frag_keyframe+empty_moov', 'pipe:1']
                filename = f"{title}.mp4"
                mimetype = "video/mp4"

        def generate():
            # STREAM from ffmpeg stdout direct to client bypassing disk
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                app.logger.error(f"Stream error: {e}")
            finally:
                process.stdout.close()
                process.terminate()
                process.wait()

        safe_filename = quote(filename.encode('utf-8'))
        headers = {
            'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}"
        }
        
        return Response(stream_with_context(generate()), mimetype=mimetype, headers=headers)
        
    except Exception as e:
        app.logger.error(f"Error downloading: {e}")
        return f"Error downloading: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
