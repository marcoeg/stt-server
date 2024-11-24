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

OpenAI Whisper:
https://github.com/openai/whisper/tree/main


## Project Structure

```
whisper_serve/
├── config.json         # Configuration file
├── setup.py            # Package setup
├── requirements.txt    # Project dependencies
├── main.py             # Application entry point
└── whisper_serve/      # Main package directory
    ├── __init__.py     # Package initialization
    ├── api.py          # FastAPI implementation
    ├── config.py       # Configuration management
    ├── logger.py       # Logging setup
    ├── models.py       # Model and transcription logic
    └── utils.py        # Utility functions
```

### Module Descriptions

- **main.py**: Application entry point, handles service deployment and lifecycle
- **api.py**: REST API interface using FastAPI
- **config.py**: Configuration management and validation
- **models.py**: Core transcription logic and model management
- **utils.py**: Audio processing and utility functions
- **logger.py**: Centralized logging configuration

## Requirements

### System Requirements
- Python 3.10 or higher
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

1. Clone the repository:
```bash
git clone https://github.com/marcoeg/whisper-serve.git
cd whisper-serve
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  
```

3. Install dependencies:
```bash
# Install OpenAI Whisper
pip install openai-whisper

# Install other requirements
pip install -r requirements.txt

# Install Ray with Serve components
pip install -U "ray[default,serve]"

# Install the package in development mode
pip install -e .
```

## Configuration

The service is configured through `config.json`:

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "dedicated_cpu": true,
        "num_cpus": 4
    },
    "model": {
        "size": "base",
        "device": "auto",
        "model_dir": "models",
        "supported_formats": [".wav", ".mp3", ".m4a", ".ogg"]
    },
    "deployment": {
        "num_replicas": 4,
        "cpu_per_replica": 0.5,
        "gpu_per_replica": 0.1
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "whisper_service.log"
    }
}
```

### Configuration Options

- **Server Configuration**
  - `host`: Server binding address
  - `port`: Server port
  - `dedicated_cpu`: Whether to use dedicated CPU for serving
  - `num_cpus`: Number of CPUs to use

- **Model Configuration**
  - `size`: Whisper model size (`tiny`, `base`, `small`, `medium`, `large`)
  - `device`: Computing device (`auto`, `cuda`, `cpu`)
  - `model_dir`: Directory for model storage
  - `supported_formats`: List of supported audio formats

- **Deployment Configuration**
  - `num_replicas`: Number of service replicas
  - `cpu_per_replica`: CPU allocation per replica
  - `gpu_per_replica`: GPU allocation per replica (if available)

## Running the Service

1. Start the service:
```bash
python main.py
```

2. The service will start and listen on the configured port (default: 8000)

3. Monitor the service through the Ray dashboard (default: http://localhost:8265)

## API Usage

### Transcribe Audio
Endpoint: `POST /transcribe`

Accepts audio files in supported formats (.wav, .mp3, .m4a, .ogg)

```bash
# Basic usage
curl -X POST http://localhost:8000/transcribe \
  -F "audio_file=@/path/to/your/audio.wav"

# With additional curl options for debugging
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

### Health Check
Endpoint: `GET /health`

```bash
curl http://localhost:8000/health
```

Response:
```json
{
    "status": "healthy"
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- 400: Invalid request (unsupported file format, empty file)
- 500: Server error (transcription failed, model error)

Error response includes detailed error messages:
```json
{
    "success": false,
    "text": "",
    "latency": 0.001,
    "word_count": 0,
    "gpu_memory": 0,
    "error": "Error message details"
}
```

## Monitoring and Logging

- Logs are written to the configured log file (default: whisper_service.log)
- Ray dashboard provides service metrics and monitoring
- Health check endpoint for service status monitoring
- Console output for immediate feedback

## Production Deployment Considerations

1. **Resource Allocation**
   - Adjust `num_replicas` based on expected load
   - Configure `cpu_per_replica` and `gpu_per_replica` based on available resources
   - Monitor memory usage and adjust accordingly

2. **Security**
   - Deploy behind a reverse proxy
   - Implement authentication if needed
   - Configure CORS appropriately

3. **Monitoring**
   - Set up log aggregation
   - Monitor Ray dashboard metrics
   - Implement alerting based on health checks

4. **Performance**
   - Use appropriate model size for your needs
   - Configure batch processing if needed
   - Monitor and adjust resource allocation

### Load Test Results
| Concurrency | Avg Latency | P95 Latency | Error Rate | % Change |
|-------------|-------------|-------------|------------|----------|
| 4           | 0.90       | 0.00       | 0.0%      | +5.9%    |
| 8           | 0.99       | 0.00       | 0.0%      | -12.4%   |
| 16          | 0.75       | 0.00       | 0.0%      | +1.4%    |
| 32          | 1.31       | 2.33       | 0.0%      | -9.7%    |
| 64          | 2.52       | 4.57       | 0.0%      | -5.6%    |
| 128         | 4.99       | 9.19       | 0.0%      | -2.9%    |
| 192         | 7.55       | 14.27      | 0.0%      | +0.1%    |
| 256         | 10.10      | 19.00      | 0.0%      | 0%       |
| 512         | 20.20      | 38.27      | 0.0%      | +0.5%    |

```
GPU Information:
Model: NVIDIA RTX 5000 Ada Generation Laptop GPU
Total Memory: 16 GB
```
---
| Concurrency | Avg Latency (s) | P95 Latency (s) | Error Rate (%) |
|-------------|-----------------|-----------------|----------------|
| 4           | 0.61            | 0.00            | 0.0%           |
| 8           | 0.93            | 0.00            | 0.0%           |
| 16          | 0.85            | 0.00            | 0.0%           |
| 32          | 1.11            | 1.99            | 0.0%           |
| 64          | 2.38            | 4.20            | 0.0%           |
| 128         | 4.31            | 8.03            | 0.0%           |
| 192         | 6.87            | 12.88           | 0.0%           |
| 256         | 9.04            | 16.88           | 0.0%           |
| 512         | 17.63           | 33.19           | 0.0%           |


```
GPU Information:
Model: NVIDIA GeForce RTX 4090
Total Memory: 24 GB
```
## License

Proprietary software. Copyright (c) 2024 Graziano Labs Corp. All rights reserved.

## Contact

Marco Graziano - marco@graziano.com

Project Link: [https://github.com/yourusername/whisper-serve](https://github.com/yourusername/whisper-serve)

---
---


## Improvements


1. **Robustness Improvements**:
   - Health check endpoints to monitor service status
   - Circuit breakers for external dependencies
   - Rate limiting to prevent abuse
   - Request ID tracking for better debugging
   - Metrics collection (latency, success rate, GPU usage, etc.)
   - Memory monitoring and cleanup
   - Proper exception handling and custom error classes
   - Input validation and sanitization
   - Maximum file size limits
   - Timeout handling
   - Dead letter queue for failed transcriptions
   - Resource quotas and limits
   - Auto-scaling based on queue size and load
   - Graceful degradation under heavy load

2. **Logging Improvements**:
   - Structured logging with JSON format
   - Different log levels (DEBUG, INFO, WARNING, ERROR)
   - Rotating log files with size/time-based rotation
   - Separate logs for:
     - Application logs
     - Access logs
     - Error logs
     - Performance metrics
   - Request/Response logging with sanitization
   - Correlation IDs for request tracking
   - Log aggregation support (ELK, CloudWatch, etc.)
   - Performance logging (GPU utilization, memory usage)
   - Audit logging for security events

3. **Additional Production Features**:
   - Authentication and authorization
   - API versioning
   - CORS configuration
   - SSL/TLS support
   - Docker containerization
   - Kubernetes deployment manifests
   - CI/CD pipeline configuration
   - Monitoring and alerting setup
   - Backup and recovery procedures
   - Documentation (API, deployment, monitoring)
   - Load balancing configuration
   - Cache management
   - Support for distributed tracing

-----

For deploying to a cluster, the main differences would be:

1. **Ray Cluster Setup**:
   - Replace local `ray.init()` with cluster connection
   - Use Ray's cluster configuration YAML
   - Define node resources and roles (head/worker nodes)
   - Configure cross-node networking

2. **Resource Management**:
   - Add node affinity for GPU workloads
   - Configure per-node replica placement
   - Adjust memory settings for distributed setup
   - Handle cross-node resource allocation

3. **Model Management**:
   - Implement model sharding across nodes
   - Add model synchronization mechanisms
   - Configure model caching per node
   - Handle model replication strategy

4. **Networking**:
   - Add load balancer configuration
   - Configure inter-node communication
   - Handle cross-node request routing
   - Implement service discovery

5. **Monitoring & Logging**:
   - Add distributed tracing
   - Implement cluster-wide logging
   - Add node health monitoring
   - Configure metrics aggregation

6. **Fault Tolerance**:
   - Add node failure handling
   - Implement request retry logic
   - Configure fallback strategies
   - Handle partial cluster failures

7. **Configuration**:
   - Add cluster-specific configurations
   - Handle per-node settings
   - Configure resource distribution
   - Add deployment strategies

Most of the application code would remain the same, with changes primarily in:
- Initialization and setup code
- Resource configuration
- Deployment scripts
- Monitoring setup

The core transcription logic would be unchanged.
