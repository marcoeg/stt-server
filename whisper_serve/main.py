from fastapi import FastAPI
from models import WhisperTranscriber
from api import WhisperAPI
from logger import logger
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WhisperService")

app = FastAPI()

# Define the deployments
transcriber = WhisperTranscriber.bind(model_size="large")  
app = WhisperAPI.bind(transcriber=transcriber) 
