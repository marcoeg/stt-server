# stt-server
Whisper speech to text scalable server


Start the service:
```bash
python whisper_serve.py --model base
```

The service will be available at http://localhost:8000/transcribe

```bash
# Basic usage with a WAV file
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav"

# Specify content type explicitly (useful for some audio formats)
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@/path/to/your/audio.mp3;type=audio/mpeg"

# Save the response to a file
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav" \
  -o transcription_result.json

# Pretty print the JSON response using jq (if installed)
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav" | jq '.'
  ```

The response will be JSON with this structure:
```json
{
  "success": true,
  "text": "transcribed text will appear here",
  "latency": 1.234,
  "word_count": 42,
  "gpu_memory": 0.5,
  "error": null
}
```

 to test with a specific duration or check the performance:
 ```bash
 # Time the request
time curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav"

# Include verbose output to see timing details
curl -v -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav"
```
The service accepts .wav, .mp3, .m4a, and .ogg files.