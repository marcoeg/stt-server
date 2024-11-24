import requests

# Send audio file for transcription
with open("./audio/test_audio.wav", "rb") as f:
    files = {"audio_file": f}
    response = requests.post("http://localhost:8000/transcribe", files=files)
    result = response.json()
    print(result)