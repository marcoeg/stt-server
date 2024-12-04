import asyncio
import aiohttp
import time
import statistics
import os
from typing import List, Dict
from dataclasses import dataclass
from pathlib import Path

import os
global ENDPOINT

#ENDPOINT = "http://" + os.getenv("RAY_HEAD_ADDRESS", "localhost") + ":8000/transcribe"
ENDPOINT = "https://marcoeg--whisper-transcription-transcribe.modal.run"

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

async def send_request(
    session: aiohttp.ClientSession, 
    audio_path: str,
    model_size: str = "base",
    language: str = "en"
) -> float:
    start_time = time.time()
    try:
        data = aiohttp.FormData()
        data.add_field('audio_file', open(audio_path, 'rb'))
        data.add_field('model_size', model_size)
        data.add_field('language', language)
        
        async with session.post(ENDPOINT, data=data) as response:
            await response.text()
            return time.time() - start_time, response.status == 200
    except Exception as e:
        print(f"Error: {e}")
        return time.time() - start_time, False

async def run_concurrent_requests(
    concurrency: int, 
    audio_files: List[str],
    model_size: str = "base",
    language: str = "en"
) -> TestResult:
    async with aiohttp.ClientSession() as session:
        tasks = []
        latencies = []
        errors = 0
        total_requests = concurrency

        for _ in range(concurrency):
            audio_file = audio_files[_ % len(audio_files)]
            task = send_request(
                session, 
                audio_file, 
                model_size=model_size,
                language=language
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for latency, success in results:
            latencies.append(latency)
            if not success:
                errors += 1

        return TestResult(concurrency, latencies, errors, total_requests)

async def main():
    # Test configuration
    concurrency_levels = [4, 8, 16, 32, 64, 128, 192, 256, 512]
    audio_dir = '../audio'
    audio_files = [str(Path(audio_dir) / f) for f in ['test_audio.wav', 'test_audio.wav', 'test_audio.wav']]
    
    # Model configurations to test
    configs = [
        #{"model_size": "tiny", "language": "en"},
        #{"model_size": "base", "language": "en"},
        # Uncomment to test other configurations
        # {"model_size": "small", "language": "en"},
        # {"model_size": "medium", "language": "en"},
        {"model_size": "large", "language": "en"},
    ]

    for config in configs:
        print(f"\nStarting load test for model_size={config['model_size']}, language={config['language']}")
        print(f"{'Concurrency':<10} {'Avg Latency':<12} {'P95 Latency':<12} {'Error Rate':<10}")
        print("-" * 44)

        for concurrency in concurrency_levels:
            result = await run_concurrent_requests(
                concurrency, 
                audio_files,
                model_size=config['model_size'],
                language=config['language']
            )
            print(f"{result.concurrency:<10} {result.avg_latency:.<12.2f} "
                  f"{result.p95_latency:.<12.2f} {result.error_rate:.<10.1f}%")

if __name__ == "__main__":
    asyncio.run(main())