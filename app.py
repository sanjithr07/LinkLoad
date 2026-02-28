import os
import subprocess
import logging
from urllib.parse import quote
from flask import Flask, request, jsonify, Response, stream_with_context, render_template
import yt_dlp

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.INFO)


def get_ffmpeg():
    """Return ffmpeg path — local .exe on Windows dev, system binary on Linux/Docker."""
    local = os.path.join(app.root_path, 'ffmpeg.exe')
    return local if os.path.exists(local) else 'ffmpeg'


# ---------------------------------------------------------------------------
# yt-dlp base options that bypass YouTube bot-detection on server IPs.
#
# Why these work:
#   - tv_embedded / ios / android_vr are non-web player clients that YouTube
#     doesn't apply the same bot-check pipeline to.
#   - 'web' and 'default' are flagged on datacenter IPs → removed from chain.
#   - A real-looking User-Agent + Accept-Language stops the "sign-in" redirect.
#   - http_chunk_size keeps large streams stable on Render/Docker.
# ---------------------------------------------------------------------------
YT_EXTRACTOR_ARGS = {
    'youtube': {
        # Priority order: tv_embedded is most permissive on server IPs,
        # ios & android_vr as fallbacks; web_creator last resort.
        'player_client': ['tv_embedded', 'ios', 'android_vr', 'web_creator'],
        # Skip any format that requires a signed URL (helps avoid 403s)
        'skip_dash_manifest': [],
    }
}

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

BASE_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': YT_EXTRACTOR_ARGS,
    'http_headers': BROWSER_HEADERS,
    # Retry network errors aggressively
    'retries': 5,
    'fragment_retries': 5,
    'http_chunk_size': 10 * 1024 * 1024,  # 10 MB chunks
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {
        **BASE_YDL_OPTS,
        'skip_download': True,
        'ffmpeg_location': get_ffmpeg(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            'title':     info.get('title', 'Unknown Title'),
            'thumbnail': info.get('thumbnail', ''),
            'duration':  info.get('duration', 0),
            'extractor': info.get('extractor_key', 'Unknown'),
        })
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        app.logger.error(f"yt-dlp info error: {err}")
        # Surface a clean message for common bot-check failures
        if 'Sign in' in err or 'bot' in err.lower():
            return jsonify({'error': 'YouTube is blocking this server. Try a different video or use a direct link.'}), 403
        return jsonify({'error': err}), 400
    except Exception as e:
        app.logger.error(f"Info error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/api/download', methods=['GET'])
def download():
    url        = request.args.get('url')
    media_type = request.args.get('type', 'video')
    quality    = request.args.get('quality', 'high')

    if not url:
        return 'URL required', 400

    is_audio = (media_type == 'audio')
    ffmpeg   = get_ffmpeg()

    # Build format selector
    if is_audio:
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        h = {'low': 480, 'medium': 720, 'high': 1080}.get(quality)
        if h:
            format_str = (
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]'
                f'/bestvideo[height<={h}]+bestaudio'
                f'/best[height<={h}]/best'
            )
        else:
            format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

    ydl_opts = {
        **BASE_YDL_OPTS,
        'format': format_str,
        'skip_download': True,
        'ffmpeg_location': ffmpeg,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info  = ydl.extract_info(url, download=False)
            title = info.get('title', 'download')

            # Collect stream URLs (video+audio or single)
            if 'requested_formats' in info:
                stream_urls = [f['url'] for f in info['requested_formats']]
            else:
                stream_urls = [info['url']]

        if is_audio:
            cmd = [
                ffmpeg, '-i', stream_urls[0],
                '-vn', '-q:a', '2', '-f', 'mp3', 'pipe:1',
            ]
            filename = f"{title}.mp3"
            mimetype = 'audio/mpeg'
        else:
            if len(stream_urls) == 2:
                cmd = [
                    ffmpeg,
                    '-i', stream_urls[0],   # video
                    '-i', stream_urls[1],   # audio
                    '-c', 'copy',
                    '-f', 'mp4',
                    '-movflags', 'frag_keyframe+empty_moov',
                    'pipe:1',
                ]
            else:
                cmd = [
                    ffmpeg, '-i', stream_urls[0],
                    '-c', 'copy',
                    '-f', 'mp4',
                    '-movflags', 'frag_keyframe+empty_moov',
                    'pipe:1',
                ]
            filename = f"{title}.mp4"
            mimetype = 'video/mp4'

        def generate():
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            try:
                while True:
                    chunk = process.stdout.read(65536)  # 64 KB chunks
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
            'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}",
        }

        return Response(
            stream_with_context(generate()),
            mimetype=mimetype,
            headers=headers,
        )

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        app.logger.error(f"yt-dlp download error: {err}")
        if 'Sign in' in err or 'bot' in err.lower():
            return 'YouTube is blocking this server. Try a different video.', 403
        return f'Download error: {err}', 400
    except Exception as e:
        app.logger.error(f"Download error: {e}")
        return f'Error: {str(e)}', 400


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
