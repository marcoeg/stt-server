import time
import statistics
import random
import asyncio
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
import aiohttp
import matplotlib.pyplot as plt

RAY_SERVE_URL = "http://127.0.0.1:8000"

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

async def send_transcribe_request(audio_path: str) -> Tuple[float, bool]:
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('audio_file', open(audio_path, 'rb'))
            async with session.post(
                f'{RAY_SERVE_URL}/transcribe',
                data=data,
                timeout=3600
            ) as response:
                await response.read()
                return time.time() - start_time, response.status == 200
    except Exception as e:
        print(f"Transcribe error: {e}")
        return time.time() - start_time, False

async def send_generate_request(prompt: str) -> Tuple[float, bool]:
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"prompt": prompt}
            async with session.post(
                f'{RAY_SERVE_URL}/generate',
                json=payload,
                timeout=3600
            ) as response:
                await response.read()
                return time.time() - start_time, response.status == 200
    except Exception as e:
        print(f"Generate error: {e}")
        return time.time() - start_time, False

async def run_concurrent_requests(
    concurrency: int,
    mode: str,
    audio_files: List[str],
    prompts: List[str]
) -> TestResult:
    tasks = []
    for i in range(concurrency):
        if mode == "transcribe":
            audio = random.choice(audio_files)
            tasks.append(send_transcribe_request(audio))
        elif mode == "generate":
            prompt = random.choice(prompts)
            tasks.append(send_generate_request(prompt))
        else:
            raise ValueError(f"Invalid mode: {mode}")

    results = await asyncio.gather(*tasks)

    latencies = []
    errors = 0
    for latency, success in results:
        latencies.append(latency)
        if not success:
            errors += 1

    return TestResult(concurrency, latencies, errors, concurrency)

def plot_results(results: List[TestResult], mode: str):
    concurrencies = [r.concurrency for r in results]
    avg_latencies = [r.avg_latency for r in results]
    p95_latencies = [r.p95_latency for r in results]

    plt.figure(figsize=(10, 6))
    plt.plot(concurrencies, avg_latencies, marker='o', label='Avg Latency')
    plt.plot(concurrencies, p95_latencies, marker='s', label='P95 Latency')
    plt.title(f"Latency vs Concurrency ({mode.capitalize()} Mode)")
    plt.xlabel("Concurrency")
    plt.ylabel("Latency (seconds)")
    plt.legend()
    plt.grid(True)
    plt.show()

async def run_mixed_concurrent_requests_separated(
    concurrency: int,
    audio_files: List[str],
    prompts: List[str]
) -> Tuple[TestResult, TestResult]:
    """
    Run concurrent requests, but track transcribe and generate latencies separately.
    """
    transcribe_tasks = []
    generate_tasks = []

    for i in range(concurrency):
        if i % 2 == 0:
            audio = random.choice(audio_files)
            transcribe_tasks.append(send_transcribe_request(audio))
        else:
            prompt = random.choice(prompts)
            generate_tasks.append(send_generate_request(prompt))

    # Run both types concurrently
    all_tasks = transcribe_tasks + generate_tasks
    results = await asyncio.gather(*all_tasks)

    # Now separate the results
    transcribe_latencies = []
    transcribe_errors = 0
    generate_latencies = []
    generate_errors = 0

    for idx, (latency, success) in enumerate(results):
        if idx < len(transcribe_tasks):
            transcribe_latencies.append(latency)
            if not success:
                transcribe_errors += 1
        else:
            generate_latencies.append(latency)
            if not success:
                generate_errors += 1

    transcribe_result = TestResult(
        concurrency=len(transcribe_tasks),
        latencies=transcribe_latencies,
        errors=transcribe_errors,
        total_requests=len(transcribe_tasks)
    )

    generate_result = TestResult(
        concurrency=len(generate_tasks),
        latencies=generate_latencies,
        errors=generate_errors,
        total_requests=len(generate_tasks)
    )

    return transcribe_result, generate_result

import matplotlib.pyplot as plt

def plot_combined_avg_latencies(transcribe_results, generate_results):
    concurrencies = [r.concurrency for r in transcribe_results]
    transcribe_avg_latencies = [r.avg_latency for r in transcribe_results]
    generate_avg_latencies = [r.avg_latency for r in generate_results]

    plt.figure(figsize=(10, 6))
    plt.plot(concurrencies, transcribe_avg_latencies, marker='o', label='Transcribe Avg Latency')
    plt.plot(concurrencies, generate_avg_latencies, marker='s', label='Generate Avg Latency')

    plt.title("Average Latency vs Concurrency (Mixed Load)")
    plt.xlabel("Concurrency")
    plt.ylabel("Average Latency (seconds)")
    plt.legend()
    plt.grid(True)
    plt.show()

def main():
    concurrency_levels = [2,3, 4,5,6,7, 8,9, 10, 12, 14, 16, 18, 20]
    audio_dir = '../audio'
    audio_files = [str(p) for p in Path(audio_dir).glob('*.wav')]
    if not audio_files:
        raise ValueError("No audio files found in the specified directory.")

    prompts = [
        "Tell me a short story about a robot who learns to cook in 40 characters.",
        "What is the capital of France? only the name.",
        "Explain quantum entanglement in simple terms in 50 characters.",
        "Write a haiku about the ocean of 4 words.",
        "List five healthy snacks for kids. only the initials"
    ]

    # simpler prompts
    prompts = [
        "What is 2 plus 2?",
        "What color is the sky?",
        "Name the largest ocean.",
        "What is the capital of Japan?",
        "What is the first letter of the alphabet?",
        "What is the freezing point of water?",
        "What day comes after Monday?",
        "How many legs does a spider have?",
        "Which planet is closest to the sun?",
        "What is the color of grass?"
    ]


    for mode in ["transcribe", "generate"]:
        print(f"\nStarting load test ({mode.upper()} mode)...")
        print(f"{'Concurrency':<10} {'Avg Latency':<12} {'P95 Latency':<12} {'Error Rate':<10}")
        print("-" * 44)

        results = []

        for concurrency in concurrency_levels:
            result = asyncio.run(run_concurrent_requests(
                concurrency=concurrency,
                mode=mode,
                audio_files=audio_files,
                prompts=prompts
            ))

            print(f"{result.concurrency:<10} {result.avg_latency:.<12.2f} "
                  f"{result.p95_latency:.<12.2f} {result.error_rate:.<10.1f}%")
            results.append(result)

        plot_results(results, mode)

    ### New section: Mixed load testing
    print(f"\nStarting MIXED load test (Transcribe + Generate separately)...")
    print(f"{'Concurrency':<10} {'Avg Lat T':<12} {'P95 Lat T':<12} {'Err Rate T':<10} || {'Avg Lat G':<12} {'P95 Lat G':<12} {'Err Rate G':<10}")
    print("-" * 100)

    transcribe_results = []
    generate_results = []

    for concurrency in concurrency_levels:
        transcribe_result, generate_result = asyncio.run(run_mixed_concurrent_requests_separated(
            concurrency=concurrency,
            audio_files=audio_files,
            prompts=prompts
        ))

        print(f"{concurrency:<10} "
              f"{transcribe_result.avg_latency:.<12.2f} {transcribe_result.p95_latency:.<12.2f} {transcribe_result.error_rate:.<10.1f}% || "
              f"{generate_result.avg_latency:.<12.2f} {generate_result.p95_latency:.<12.2f} {generate_result.error_rate:.<10.1f}%")

        transcribe_results.append(transcribe_result)
        generate_results.append(generate_result)

    plot_combined_avg_latencies(transcribe_results, generate_results)

    #plot_results(transcribe_results, mode="transcribe-mixed")
    #plot_results(generate_results, mode="generate-mixed")


if __name__ == "__main__":
    main()
