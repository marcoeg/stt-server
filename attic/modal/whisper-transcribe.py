import torch
import whisper
from pathlib import Path
from typing import Optional, Union
import soundfile as sf
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

def load_whisper_model(model_size: str = "base") -> whisper.Whisper:
    """
    Load and return a Whisper model.
    
    Args:
        model_size (str): Size of the model to load. Options: "tiny", "base", "small", 
                         "medium", "large". Defaults to "base".
    
    Returns:
        whisper.Whisper: Loaded Whisper model
    
    Raises:
        ValueError: If invalid model size is provided
    """
    valid_models = ["tiny", "base", "small", "medium", "large"]
    
    if model_size not in valid_models:
        raise ValueError(f"Invalid model size. Choose from: {', '.join(valid_models)}")
    
    # Check if CUDA is available and set device accordingly
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load the model
    try:
        model = whisper.load_model(model_size).to(device)
        print(f"Successfully loaded {model_size} model")
        return model
    except Exception as e:
        raise Exception(f"Error loading model: {str(e)}")

def transcribe_audio(
    model: whisper.Whisper,
    audio_data: np.ndarray,
    sample_rate: int,
    language: Optional[str] = None,
    task: str = "transcribe"
) -> dict:
    """
    Transcribe audio data using the loaded Whisper model.
    
    Args:
        model (whisper.Whisper): Loaded Whisper model
        audio_data (np.ndarray): Audio data as numpy array
        sample_rate (int): Sample rate of the audio data
        language (Optional[str]): Language code (e.g., "en" for English). 
                                If None, language will be auto-detected
        task (str): Task to perform - "transcribe" or "translate". 
                   Defaults to "transcribe"
    
    Returns:
        dict: Dictionary containing transcription results
    
    Raises:
        ValueError: If invalid task is specified or audio data is invalid
    """
    # Verify task
    if task not in ["transcribe", "translate"]:
        raise ValueError('Task must be either "transcribe" or "translate"')
    
    try:
        # Verify audio data
        if not isinstance(audio_data, np.ndarray):
            raise ValueError("Audio data must be a numpy array")
        
        # Convert audio data to float32 (required by Whisper)
        audio_data = audio_data.astype(np.float32)
        
        # Perform transcription
        options = {"task": task}
        if language:
            options["language"] = language
            
        result = model.transcribe(audio_data, **options)
        return result
    except Exception as e:
        raise Exception(f"Error during transcription: {str(e)}")

def read_audio_file(audio_path: Union[str, Path]) -> tuple[np.ndarray, int]:
    """
    Read an audio file and return the audio data and sample rate.
    
    Args:
        audio_path (Union[str, Path]): Path to the audio file
    
    Returns:
        tuple: (audio_data: np.ndarray, sample_rate: int)
    
    Raises:
        FileNotFoundError: If audio file doesn't exist
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    try:
        # Read the audio file
        audio_data, sample_rate = sf.read(str(audio_path))
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        # Ensure data type is float32
        audio_data = audio_data.astype(np.float32)
        
        return audio_data, sample_rate
    except Exception as e:
        raise Exception(f"Error reading audio file: {str(e)}")

def main():
    """
    Main function to test the Whisper transcription functionality.
    """
    # Example usage
    try:
        # Load the model
        model = load_whisper_model("large")
        
        # Example audio file path - replace with your audio file
        audio_file = "/home/marco/Development/mglabs/stt-server/audio/test_audio.wav"
        
        # Read the audio file
        print("Reading audio file...")
        audio_data, sample_rate = read_audio_file(audio_file)
        
        # Perform transcription
        print("Transcribing audio...")
        result = transcribe_audio(
            model=model,
            audio_data=audio_data,
            sample_rate=sample_rate,
            language="en"  # Optional: specify language
        )
        
        # Print results
        print("\nTranscription Results:")
        print("-" * 50)
        print(f"Detected language: {result.get('language', 'Unknown')}")
        print(f"Transcription: {result.get('text', '')}")
        
        # Print segments if available
        if 'segments' in result:
            print("\nSegments:")
            for segment in result['segments']:
                print(f"\nTimestamp [{segment['start']:.2f}s - {segment['end']:.2f}s]:")
                print(f"Text: {segment['text']}")
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()