import modal
import time
import statistics
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Define the Modal app
app = modal.App("whisper-loadtest")

@dataclass
class TestResult:
    concurrency: int
    latencies: List[float]
    errors: int
    total_requests: int

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def p95_latency(self) -> float:
        return statistics.quantiles(self.latencies, n=20)[18] if len(self.latencies) >= 20 else 0

    @property
    def error_rate(self) -> float:
        return (self.errors / self.total_requests) * 100 if self.total_requests > 0 else 0

@app.function(timeout=600)
def send_request(input_tuple: Tuple[str, str, str]) -> Tuple[float, bool]:
    """
    Send a single request to the transcription service.
    Returns (latency, success).
    """
    import aiohttp
    import asyncio
    
    audio_path, model_size, language = input_tuple
    
    async def _send():
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('audio_file', open(audio_path, 'rb'))
                data.add_field('model_size', model_size)
                data.add_field('language', language)
                
                async with session.post(
                    'https://marcoeg--whisper-transcription-transcribe.modal.run',
                    data=data
                ) as response:
                    await response.text()
                    return time.time() - start_time, response.status == 200
        except Exception as e:
            print(f"Error: {e}")
            return time.time() - start_time, False

    return asyncio.run(_send())

@app.function()
def run_concurrent_requests(concurrency: int, audio_files: List[str], model_size: str = "base", language: str = "en") -> TestResult:
    """Run concurrent requests using Modal's parallel execution"""
    # Create input tuples for each request
    inputs = [
        (audio_files[i % len(audio_files)], model_size, language)
        for i in range(concurrency)
    ]
    
    # Run requests in parallel using Modal's map
    results = list(send_request.map(inputs))
    
    # Process results
    latencies = []
    errors = 0
    for latency, success in results:
        latencies.append(latency)
        if not success:
            errors += 1
    
    return TestResult(concurrency, latencies, errors, concurrency)

@app.local_entrypoint()
def main():
    concurrency_levels = [4, 8, 16, 32, 64, 128]
    audio_dir = '../audio'
    audio_files = [str(Path(audio_dir) / f) for f in ['test_audio.wav']]
    model_size = "base"
    language = "en"

    print("\nStarting load test...")
    print(f"{'Concurrency':<10} {'Avg Latency':<12} {'P95 Latency':<12} {'Error Rate':<10}")
    print("-" * 44)

    for concurrency in concurrency_levels:
        result = run_concurrent_requests.remote(
            concurrency=concurrency, 
            audio_files=audio_files,
            model_size=model_size,
            language=language
        )
        
        print(f"{result.concurrency:<10} {result.avg_latency:.<12.2f} "
              f"{result.p95_latency:.<12.2f} {result.error_rate:.<10.1f}%")

if __name__ == "__main__":
    modal.runner.main()