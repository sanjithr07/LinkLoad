# LinkLoad

A very minimal, personal media downloader web app built with Flask and `yt-dlp`. You can paste any link (YouTube, TikTok, Instagram, Twitter, etc.) and it will auto-detect the video and provide options to download as audio or video, in different qualities.

## Features
- **Zero-Disk Streaming:** Direct FFmpeg pipe generation. Downloads bypass server storage and instantly stream back to your browser client flawlessly upon fetch. 
- **Auto-Detection:** Uses `yt-dlp` to extract thumbnail, title, and media format information.
- **Universal Downloading:** Supports over 1000 websites.
- **Audio & Video support:** Extract high-quality video or just the audio.
- **Quality Selector:** Choose between Basic, Standard, High, and Premium qualities.
- **Minimal Aesthetic UI:** Clean, glassmorphism dark mode interface built with Vanilla CSS and JS.
- **Containerized:** Production-ready `Dockerfile` & Blueprint deployment designed directly for Render.

## Tech Stack
- **Backend:** Python 3.11, Flask, yt-dlp, FFmpeg, Gunicorn
- **Frontend:** HTML, Vanilla CSS (Glassmorphism UI), Vanilla JS

---

## Running Locally (Windows)

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install local `ffmpeg.exe` (Run the provided helper script):
   ```bash
   python install_ffmpeg.py
   ```
5. Run the app:
   ```bash
   python app.py
   ```
6. Open `http://localhost:5000` in your browser.

---

## Deploying to Render (Free Tier)

This app is pre-configured to automatically deploy as a robust Docker process.
1. Push this code to a new GitHub repository.
2. Sign up / Login at [Render](https://render.com/).
3. Create a **New Blueprint**.
4. Connect the GitHub repository.
5. Render will automatically detect `render.yaml`, read the Docker instructions (installing Linux `ffmpeg` inside the container), and launch your site for free!

*(Note: Render free instances sleep after 15 mins of inactivity. Ping your deployed instance with UptimeRobot or cron-job.org to keep it awake!)*
