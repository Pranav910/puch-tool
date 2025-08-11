import subprocess
import os
import multiprocessing

# === CONFIG ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
TRANSCRIPT_DIR = os.path.join(BASE_DIR, "transcripts")

# Ensure folders exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/watch?v=JcVHf4X_dqY"  # Replace with your video
AUDIO_FILE = os.path.join(DOWNLOAD_DIR, "audio.wav")
FAST_AUDIO_FILE = os.path.join(DOWNLOAD_DIR, "audio_fast.wav")
WHISPER_CLI = r"D:\whisperproject\whisper.cpp\bin\Release\whisper-cli.exe"
MODEL_FILE = r"D:\whisperproject\whisper.cpp\models\ggml-tiny-q8_0.bin"
PLAYBACK_SPEED = 2.5

num_threads = multiprocessing.cpu_count()
print(f"Using {num_threads} threads for transcription...")

def download_audio(url, audio_file):
    """
    Download best audio from YouTube and convert to 16kHz mono WAV using ffmpeg.
    """
    print("[INFO] Downloading and converting audio...")
    cmd = (
      f'yt-dlp -f bestaudio -o - "{url}" | '
      f'ffmpeg -i pipe:0 -ar 16000 -ac 1 -f wav "{audio_file}" -y'
    )
    subprocess.run(cmd, shell=True, check=True)

def speed_up_audio(input_file, output_file, speed_factor):
    """
    Speed up audio by speed_factor using ffmpeg atempo filter.
    Max per filter is 2.0, so chain if higher.
    """
    print(f"[INFO] Speeding up audio by {speed_factor}x...")
    filters = []
    remaining = speed_factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    filters.append(f"atempo={remaining}")
    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-i", input_file,
        "-filter:a", filter_str,
        "-ar", "16000", "-ac", "1",
        output_file, "-y"
    ]
    subprocess.run(cmd, check=True)

def transcribe_with_whisper(audio_file, model_file):
    """
    Transcribe audio using whisper.cpp CLI and save transcript in transcripts folder.
    """
    print("[INFO] Transcribing with whisper.cpp...")
    output_path = os.path.join(TRANSCRIPT_DIR, "transcript.txt")

    cmd = [
    WHISPER_CLI,
    "-m", MODEL_FILE,
    "-f", FAST_AUDIO_FILE,
    "-t", str(num_threads),  # Use all CPU cores
    "-otxt",  # Output as text
    "-of", TRANSCRIPT_DIR.replace(".txt", "")  # whisper.cpp auto adds .txt
]
    subprocess.run(cmd, check=True)

    generated_txt = audio_file + ".txt"
    if os.path.exists(generated_txt):
        os.replace(generated_txt, output_path)
        with open('transcripts.txt', "r", encoding="utf-8") as f:
            transcript = f.read()
        return transcript
    else:
        return "[ERROR] Transcript file not found."

if __name__ == "__main__":
    # Step 1: Download and convert audio
    download_audio(VIDEO_URL, AUDIO_FILE)

    # Step 2: Speed up audio for faster transcription
    speed_up_audio(AUDIO_FILE, FAST_AUDIO_FILE, PLAYBACK_SPEED)

    # Step 3: Transcribe sped-up audio
    transcript = transcribe_with_whisper(FAST_AUDIO_FILE, MODEL_FILE)

    with open('transcripts.txt', "r", encoding="utf-8") as f:
      transcript = f.read()
      # Step 4: Show transcript
      print("\n===== TRANSCRIPT =====")
      print(transcript)
      # return transcript
      
