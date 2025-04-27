from ray import serve
from whisper_serve.api import RootApp
from whisper_serve.models import WhisperTranscriber, Llama3Inference

def root_app(args):
    whisper_model = WhisperTranscriber.bind(**args["whisper_model_args"])
    llama_model = Llama3Inference.bind(**args["llama_model_args"])
    return RootApp.bind(whisper_model, llama_model)
