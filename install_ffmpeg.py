import os
import urllib.request
import zipfile
import shutil

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"
print("Downloading ffmpeg...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(".")

# Find the bin folder
extracted_folder = [f for f in os.listdir() if f.startswith('ffmpeg-master-latest-win64-gpl') and os.path.isdir(f)][0]
bin_dir = os.path.join(extracted_folder, 'bin')

# Move ffmpeg.exe and ffprobe.exe to current dir
shutil.copy(os.path.join(bin_dir, 'ffmpeg.exe'), 'ffmpeg.exe')
shutil.copy(os.path.join(bin_dir, 'ffprobe.exe'), 'ffprobe.exe')

# Cleanup
print("Cleaning up...")
shutil.rmtree(extracted_folder)
os.remove(zip_path)
print("Done! ffmpeg and ffprobe are ready.")
