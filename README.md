# Whisper Serve

A distributed speech-to-text service using OpenAI's Whisper model, built with Ray Serve for scalable deployment.

Author: Marco Graziano (marco@graziano.com)  
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.

## Overview

Whisper Serve provides a production-ready REST API for speech-to-text transcription using OpenAI's Whisper model. Built on Ray Serve, it offers:
- Distributed processing with automatic resource management
- Configurable deployment options
- Production-ready logging and monitoring
- Efficient model management and caching
- RESTful API interface
- Health monitoring endpoints

For more information about OpenAI Whisper:
https://github.com/openai/whisper/tree/main

## Project Structure

```
.
├── audio/                  # Test audio files
│   └── test_audio.wav
|   ├── test_audio10.wav
|   └── test_audio30.wav 
├── models/               # Whisper models cache 
│   ├── base.pt           
│   └── large.pt         
├── whisper_serve/        # Main package
│   ├── __init__.py
│   ├── api.py            # FastAPI implementation
│   ├── config.py         # Configuration management
│   ├── logger.py         # Logging setup
│   ├── models.py         # Model and transcription logic
│   └── utils.py          # Utility functions
├── tests/                # Test suite
│   ├── load_test.py      # Cluster load test
│   └── combo_load_test.py    # Combo test
├── README.md             # Project documentation
├── requirements.txt      # Project dependencies
└── serve_config.local.yaml     # Ray whisper_serv configuration
```

## Requirements

### System Requirements
- Python 3.9 (strict)
- CUDA-compatible GPU (optional, for GPU acceleration)
- Sufficient disk space for model storage
- Adequate RAM (minimum 8GB recommended)

### Dependencies
The project requires several key packages:
- openai-whisper: OpenAI's speech recognition model
- Ray with Serve components for distributed serving
- FastAPI for REST API
- Additional utilities for audio processing and API handling

## Installation
Follow the steps in [INSTALL.md](INSTALL.md) to set up the environment and deploy.

## Ray Serve Deployment

#### Local Development Setup

1. **Start Ray Cluster**
```bash
# Start the Ray head node
ray start --head

# Set dashboard address
export RAY_DASHBOARD_ADDRESS="http://127.0.0.1:8265"

# Optional: Set PYTHONPATH -- only needed when running from a different directory
export PYTHONPATH="/path/to/whisper-serve"
```

2. **Deploy Service**
```bash
# Deploy using serve configuration
serve deploy config/serve_config_local.yaml -a $RAY_DASHBOARD_ADDRESS
```

3. **Verify Deployment**
```bash
# Check service status
serve status -a $RAY_DASHBOARD_ADDRESS

# Test the service
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@./audio/test_audio.wav"
```


## API Usage

### Transcribe Audio
Endpoint: `POST /transcribe`

Accepts audio files in supported formats (.wav, .mp3, .m4a, .ogg)

```bash
# Basic usage
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav"

# With additional options
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav" \
  -v \
  --max-time 300
```

Response format:
```json
{
    "success": true,
    "text": "transcribed text appears here",
    "latency": 1.234,
    "word_count": 42,
    "gpu_memory": 0.5,
    "error": null
}
```


## Monitoring and Management

1. **Service Status**
```bash
# Check deployment status
serve status -a $RAY_DASHBOARD_ADDRESS

# List deployments
serve list -a $RAY_DASHBOARD_ADDRESS
```

2. **Ray Dashboard**
Access the dashboard at `http://<head-node-ip>:8265` to monitor:
- Node status and resources
- GPU utilization
- Running actors and tasks
- Memory usage

3. **Logs**
```bash
# Check Ray logs
tail -f /tmp/ray/session_*/logs/serve/*.log

# Check application logs
tail -f whisper_service.log
```

## Troubleshooting

1. **Service Health**
```bash
# Check service health in the Ray dashboard
http://127.0.0.1:8265/


# Check deployment status
serve status -a $RAY_DASHBOARD_ADDRESS
```

2. **Resource Verification (on nodes)**
```bash
# Check GPU status
nvidia-smi

# Verify Ray cluster status
ray status
```

## License

Proprietary software. Copyright (c) 2024 Graziano Labs Corp. All rights reserved.

## Contact

Marco Graziano - marco@graziano.com
