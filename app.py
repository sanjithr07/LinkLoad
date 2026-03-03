"""
LinkLoad – Flask backend
========================
YouTube bot-detection bypass strategy (in priority order):
  1. Cookies  – YT_COOKIES_B64 env var (base64-encoded cookies.txt)
  2. PO Token – YT_PO_TOKEN + YT_VISITOR_DATA env vars
  3. Player client chain – tv_embedded → ios → mweb → android_creator
     (works without auth for many videos, fails on restricted/age-gated ones)

Setup instructions for Render / Docker:
  1. Export YouTube cookies from your browser using the
     "Get cookies.txt LOCALLY" extension (select youtube.com, Netscape format).
  2. Base64-encode the file (PowerShell):
       [Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))
     or on Mac/Linux:
       base64 -w 0 cookies.txt
  3. In Render Dashboard → Environment → Add:
       Key:   YT_COOKIES_B64
       Value: <paste the base64 string>
  4. Redeploy — yt-dlp will authenticate as your account, bypassing all blocks.
"""

import os
import base64
import tempfile
import atexit
import logging
import subprocess
from urllib.parse import quote

from flask import Flask, request, jsonify, Response, stream_with_context, render_template
import yt_dlp

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.INFO)

# ── Cookies setup ────────────────────────────────────────────────────────────

_cookies_file: str | None = None


def _init_cookies() -> str | None:
    """
    Decode the YT_COOKIES_B64 env var and write a temp cookies.txt file.
    Returns the path to the file, or None if the env var isn't set.
    """
    global _cookies_file
    b64 = os.environ.get('YT_COOKIES_B64', '').strip()
    if not b64:
        return None
    try:
        data = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(
            mode='wb', suffix='.txt', delete=False, prefix='yt_cookies_'
        )
        tmp.write(data)
        tmp.close()
        _cookies_file = tmp.name
        app.logger.info('YouTube cookies loaded from YT_COOKIES_B64.')
    except Exception as exc:
        app.logger.warning(f'Failed to decode YT_COOKIES_B64: {exc}')
    return _cookies_file


def _cleanup_cookies():
    if _cookies_file and os.path.exists(_cookies_file):
        os.unlink(_cookies_file)


atexit.register(_cleanup_cookies)
_init_cookies()   # run at import time (works for both gunicorn + dev)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_ffmpeg() -> str:
    """Local .exe on Windows dev, system binary on Linux/Docker."""
    local = os.path.join(app.root_path, 'ffmpeg.exe')
    return local if os.path.exists(local) else 'ffmpeg'


def build_ydl_opts(**overrides) -> dict:
    """
    Build yt-dlp options with the best available auth method.
    Priority: cookies > PO token > unauthenticated player clients.
    """
    # --- Extractor args ---
    extractor_args: dict = {
        'youtube': {
            # Player client fallback chain.
            # tv_embedded and ios avoid most server-IP checks.
            # mweb and android_creator are last-resort unauthenticated options.
            'player_client': ['tv_embedded', 'ios', 'mweb', 'android_creator'],
        }
    }

    # PO token (strongest un-cookied bypass, optional)
    po_token    = os.environ.get('YT_PO_TOKEN', '').strip()
    visitor_data = os.environ.get('YT_VISITOR_DATA', '').strip()
    if po_token and visitor_data:
        extractor_args['youtube']['po_token']     = [f'web+{po_token}']
        extractor_args['youtube']['visitor_data'] = [visitor_data]
        app.logger.debug('Using PO token for YouTube requests.')

    opts = {
        'quiet':            True,
        'no_warnings':      True,
        'extractor_args':   extractor_args,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'retries':          6,
        'fragment_retries': 6,
        'http_chunk_size':  10 * 1024 * 1024,
        # ── Geo-restriction bypass ────────────────────────────────────────
        # Sends X-Forwarded-For headers spoofing an IP in the target country.
        # Set YT_GEO_BYPASS_COUNTRY to a 2-letter ISO code (e.g. IN, GB, US).
        # Defaults to IN (India) because Render runs in Oregon, US — many
        # Indian content creators region-lock to IN, and IN also covers a
        # broad range of YouTube content.
        'geo_bypass':         True,
        'geo_bypass_country': os.environ.get('YT_GEO_BYPASS_COUNTRY', 'IN'),
    }

    # Cookies → highest-priority auth, overrides everything else
    if _cookies_file:
        opts['cookiefile'] = _cookies_file

    opts['ffmpeg_location'] = get_ffmpeg()
    opts.update(overrides)
    return opts


def friendly_error(raw: str) -> tuple[str, int]:
    """
    Convert raw yt-dlp error strings into user-friendly messages + HTTP codes.
    """
    low = raw.lower()
    if 'sign in' in low or 'bot' in low or '403' in low:
        return (
            'YouTube is blocking this server. '
            'Set the YT_COOKIES_B64 environment variable to fix this — '
            'see COOKIES_SETUP.md for instructions.',
            403,
        )
    if 'private video' in low:
        return 'This video is private.', 403
    if 'age' in low and 'restrict' in low:
        return 'This video is age-restricted. Cookies from a signed-in account are required.', 403
    if 'not available' in low or 'copyright' in low or 'blocked' in low:
        return (
            'This video is not available in the server region. '
            'Try setting YT_GEO_BYPASS_COUNTRY to your country code (e.g. IN, GB, US) '
            'in Render environment variables.',
            451,
        )
    return raw, 400


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json or {}
    url  = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    opts = build_ydl_opts(skip_download=True)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            'title':     info.get('title', 'Unknown Title'),
            'thumbnail': info.get('thumbnail', ''),
            'duration':  info.get('duration', 0),
            'extractor': info.get('extractor_key', 'Unknown'),
        })

    except yt_dlp.utils.DownloadError as exc:
        msg, code = friendly_error(str(exc))
        app.logger.error(f'Info error [{code}]: {exc}')
        return jsonify({'error': msg}), code
    except Exception as exc:
        app.logger.error(f'Info error: {exc}')
        return jsonify({'error': str(exc)}), 400


@app.route('/api/download', methods=['GET'])
def download():
    url        = request.args.get('url', '').strip()
    media_type = request.args.get('type', 'video')
    quality    = request.args.get('quality', 'high')

    if not url:
        return 'URL required', 400

    is_audio = (media_type == 'audio')
    ffmpeg   = get_ffmpeg()

    # Build format selector
    if is_audio:
        fmt = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        h_map = {'low': 480, 'medium': 720, 'high': 1080}
        h = h_map.get(quality)
        if h:
            fmt = (
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]'
                f'/bestvideo[height<={h}]+bestaudio'
                f'/best[height<={h}]/best'
            )
        else:
            fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

    opts = build_ydl_opts(format=fmt, skip_download=True)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info  = ydl.extract_info(url, download=False)
            title = info.get('title', 'download')

            if 'requested_formats' in info:
                stream_urls = [f['url'] for f in info['requested_formats']]
            else:
                stream_urls = [info['url']]

        # Build ffmpeg command
        if is_audio:
            cmd      = [ffmpeg, '-i', stream_urls[0], '-vn', '-q:a', '2', '-f', 'mp3', 'pipe:1']
            filename = f'{title}.mp3'
            mimetype = 'audio/mpeg'
        else:
            base_cmd = [ffmpeg]
            if len(stream_urls) == 2:
                base_cmd += ['-i', stream_urls[0], '-i', stream_urls[1]]
            else:
                base_cmd += ['-i', stream_urls[0]]
            cmd      = base_cmd + ['-c', 'copy', '-f', 'mp4', '-movflags', 'frag_keyframe+empty_moov', 'pipe:1']
            filename = f'{title}.mp4'
            mimetype = 'video/mp4'

        def generate():
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                while chunk := proc.stdout.read(65536):
                    yield chunk
            except Exception as exc:
                app.logger.error(f'Stream error: {exc}')
            finally:
                proc.stdout.close()
                proc.terminate()
                proc.wait()

        safe_name = quote(filename.encode('utf-8'))
        return Response(
            stream_with_context(generate()),
            mimetype=mimetype,
            headers={'Content-Disposition': f"attachment; filename*=UTF-8''{safe_name}"},
        )

    except yt_dlp.utils.DownloadError as exc:
        msg, code = friendly_error(str(exc))
        app.logger.error(f'Download error [{code}]: {exc}')
        return msg, code
    except Exception as exc:
        app.logger.error(f'Download error: {exc}')
        return str(exc), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
