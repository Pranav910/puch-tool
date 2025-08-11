import os
import subprocess
from pydub import AudioSegment
import yt_dlp
import re

# === Config - update paths ===
WHISPER_CPP_EXE = r"D:\whisperproject\whisper.cpp\bin\Release\whisper-cli.exe"
WHISPER_MODEL = r"D:\whisperproject\whisper.cpp\models\ggml-base.en.bin"
DOWNLOADS_DIR = "downloads"
TRANSCRIPTS_DIR = "transcripts"

# Make sure folders exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Remove illegal characters and replace spaces with underscores for filenames."""
    # Remove invalid chars: \ / * ? : " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    sanitized = sanitized.strip().replace(" ", "_")
    return sanitized

def download_audio(youtube_url: str) -> str:
    """Download audio from YouTube as MP3, return sanitized file path."""
    # We will override outtmpl to a temp safe name and rename after download
    temp_outtmpl = os.path.join(DOWNLOADS_DIR, "temp_audio.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_outtmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        title = info.get('title', 'audio')
        sanitized_title = sanitize_filename(title)
        mp3_filename = f"{sanitized_title}.mp3"
        mp3_path = os.path.join(DOWNLOADS_DIR, mp3_filename)

        # Rename the temp downloaded file to sanitized filename
        temp_mp3_path = os.path.join(DOWNLOADS_DIR, "temp_audio.mp3")
        if os.path.exists(temp_mp3_path):
            os.rename(temp_mp3_path, mp3_path)
        else:
            raise FileNotFoundError(f"Expected temp MP3 file not found: {temp_mp3_path}")

        print(f"[INFO] Downloaded MP3 file: {mp3_path}")
        return mp3_path

def convert_mp3_to_16k_wav(mp3_path: str) -> str:
    """Convert MP3 file to 16 kHz WAV required by whisper.cpp."""
    wav_16k_path = os.path.splitext(mp3_path)[0] + "_16k.wav"
    print(f"[INFO] Converting MP3 to 16 kHz WAV: {wav_16k_path}")

    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_frame_rate(16000)  # Whisper.cpp requires 16kHz
    audio.export(wav_16k_path, format="wav")
    return wav_16k_path

def transcribe_with_whisper_cpp(wav_path: str):
    """Run whisper.cpp CLI on 16k WAV and return transcript path and content."""
    base_name = os.path.splitext(os.path.basename(wav_path))[0]
    transcript_base = sanitize_filename(base_name)
    transcript_path = os.path.join(TRANSCRIPTS_DIR, transcript_base + ".txt")

    cmd = [
        WHISPER_CPP_EXE,
        "-m", WHISPER_MODEL,
        "-f", wav_path,
        "-otxt",
        "-of", os.path.join(TRANSCRIPTS_DIR, transcript_base),
        "-t", "6"
    ]

    print("[INFO] Running whisper.cpp:")
    print(" ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("[whisper.cpp stdout]:", result.stdout)
        print("[whisper.cpp stderr]:", result.stderr)
    except subprocess.CalledProcessError as e:
        print("[ERROR] Whisper.cpp failed:")
        print(e.stdout)
        print(e.stderr)
        return None

    if not os.path.exists(transcript_path):
        print(f"[ERROR] Transcript file not found: {transcript_path}")
        return None

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    return transcript_path, transcript

def main():
    youtube_url = input("Enter YouTube video URL: ").strip()
    mp3_path = download_audio(youtube_url)
    wav_path = convert_mp3_to_16k_wav(mp3_path)
    result = transcribe_with_whisper_cpp(wav_path)

    if result is None:
        print("[FAIL] Transcription failed.")
        return

    transcript_path, transcript = result
    print(f"[SUCCESS] Transcript saved to: {transcript_path}")
    print("\n=== Transcript Preview ===")
    print(transcript[:500] + "\n...")

if __name__ == "__main__":
    main()
