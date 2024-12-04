
##
# locust -f locustfile.py --host https://marcoeg--whisper-transcription-optimized-transcribe.modal.run
# 
# locust -f locustfile.py --host https://marcoeg--whisper-transcription-optimized-transcribe.modal.run

from locust import HttpUser, task, between, LoadTestShape
import os

class WhisperTranscriptionUser(HttpUser):
    # Wait time between tasks for each user (simulates real user behavior)
    wait_time = between(1, 2)  

    @task
    def transcribe_audio(self):
        # Path to the test audio file
        file_path = "/home/marco/Development/mglabs/stt-server/audio/test_audio.wav"
        
        # Ensure the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found at: {file_path}")
        
        # Open the audio file for uploading
        with open(file_path, "rb") as audio_file:
            # Send POST request to the endpoint
            self.client.post(
                url="/",
                files={"audio_file": ("test_audio.wav", audio_file, "audio/wav")},
                data={"model_size": "large", "language": "en"},
            )

# Define a custom LoadTestShape to scale from 4 to 512 users over time
class StepLoadShape(LoadTestShape):
    """
    A step load shape with gradual increments in user count.
    """
    step_time = 30  # Time in seconds between each step
    step_users = 4  # Increment of users at each step
    max_users = 32  # Maximum number of concurrent users
    spawn_rate = 1  # Rate of spawning new users per second

    def tick(self):
        run_time = self.get_run_time()

        # Calculate the current step
        current_step = run_time // self.step_time
        user_count = 4 + current_step * self.step_users

        if user_count > self.max_users:
            return None  # Stop test once max_users is reached

        return user_count, self.spawn_rate
