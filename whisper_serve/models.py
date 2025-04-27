import ray
from ray import serve
import whisper
import torch
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
from .logger import logger
from .utils import load_audio
from vllm import LLM, SamplingParams
from huggingface_hub import login

# Make sure Hugging Face is authenticated with the API token
login(token="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")  # Replace with your actual Hugging Face token

@dataclass
class TranscriptionResult:
    success: bool
    text: str
    latency: float
    word_count: int
    gpu_memory: float
    error: Optional[str] = None

@serve.deployment
class WhisperTranscriber:
    def __init__(self, model_size: str = "base"):
        logger.info(f"Initializing WhisperTranscriber with model_size={model_size}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Use whisper library to load the model
        self.model = whisper.load_model(model_size, device=self.device)
        # ➡️ Force model to half precision if on CUDA
        #if self.device == "cuda":
        #    self.model = self.model.half()

    async def transcribe(self, audio_data: bytes) -> dict:
        start_time = time.time()

        try:
            # Load and preprocess audio
            audio = load_audio(audio_data)
            torch.cuda.empty_cache()
            # Track GPU memory usage
            start_mem = torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else 0

            # Actual transcription
            result = self.model.transcribe(audio)

            # Memory after
            end_mem = torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else 0
            memory_used = end_mem - start_mem

            logger.info("Transcription completed successfully.")

            return {
                "success": True,
                "text": result["text"],
                "latency": time.time() - start_time,
                "word_count": len(result["text"].split()),
                "gpu_memory": memory_used
            }

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

@serve.deployment
class Llama3Inference:
    def __init__(self, model_path: str):
        logger.info(f"Loading Llama 3 model from {model_path}")
        torch.cuda.empty_cache()
        # Load the Llama model using vLLM
        # self.llm = LLM(model=model_path) 
        self.llm = LLM(
            model=model_path,
            quantization="gptq",
            dtype="auto",
            enforce_eager=True,
            gpu_memory_utilization=0.6,  # optional but better
            max_num_seqs=8,  # ⬅️ smaller batch
        )

    async def generate(self, prompt: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            sampling_params = SamplingParams(
                temperature=0.1,
                top_p=0.9,
                max_tokens=512,  # Add a limit
                repetition_penalty=1.1,  # Penalize repeated outputs
                # for bigger models (like Llama-3 7B or Mistral)
                # stop=["###", "<|eot_id|>"] 
            )
            # Generating text with the model
            outputs = self.llm.generate([prompt], sampling_params)
            text = outputs[0].outputs[0].text

            return {
                "success": True,
                "text": text,
                "latency": time.time() - start_time,
            }
        except Exception as e:
            logger.error(f"Text generation error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "text": "",
                "latency": time.time() - start_time,
                "error": str(e),
            }
