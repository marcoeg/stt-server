# 📚 INSTALL.md: Full Setup Guide for Whisper-Serve with Ray and VLLM 

---

## ✨ Project Overview

This project deploys:
- **Whisper** (speech-to-text) via OpenAI Whisper models
- **Llama3** (text generation) via HuggingFace + vLLM
- Served via **Ray Serve** with GPU acceleration

This guide provides **step-by-step instructions** to replicate the environment **exactly** on any fresh machine using **pyenv** and **pyenv-virtualenv**.

---

# ✅ System Requirements

- **OS**: Ubuntu 20.04+ or any modern Linux distro
- **GPU**: NVIDIA RTX series (or better)
- **CUDA Driver Version**: >= 535.171.04 (confirmed CUDA 12.2 compatible)
- **Python**: Managed via `pyenv` (version 3.10.x)

Tested on: **NVIDIA RTX 5000 Ada Generation + CUDA 12.2 + Python 3.10**

---

# ✅ Installation Steps

## 1. Install NVIDIA Drivers (if needed)

Make sure `nvidia-smi` works and reports Driver Version ≥ 535.x:

```bash
nvidia-smi
```

If drivers are missing:
- Install via your Linux package manager (e.g., `ubuntu-drivers autoinstall`) or
- Directly download from [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)


## 2. Install pyenv and pyenv-virtualenv

Install dependencies first:

```bash
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncurses5-dev libncursesw5-dev xz-utils tk-dev \
libffi-dev liblzma-dev python-openssl git
```

Then install `pyenv` and `pyenv-virtualenv`:

```bash
curl https://pyenv.run | bash
```

Add the following to your shell startup file (e.g., `~/.bashrc`, `~/.zshrc`):

```bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Then restart your shell:

```bash
exec "$SHELL"
```


## 3. Install Python 3.9.18 with pyenv

```bash
pyenv install 3.9.18
```

Set it for your project:

```bash
pyenv local 3.9.18
```


## 4. Create a Virtual Environment

Create and activate a virtual environment:

```bash
pyenv virtualenv venv-3.9
pyenv activate venv-3.9
```

✅ You are now inside your isolated virtualenv.


## 5. Install PyTorch with CUDA 12.1 wheels

**Important:** must install the correct wheels manually:

```bash
pip install torch==2.6.0+cu121 torchvision==0.21.0+cu121 torchaudio==2.6.0+cu121 --index-url https://download.pytorch.org/whl/cu121
```


## 6. Install Project Dependencies

Install all other dependencies:

```bash
pip install -r requirements.txt
```


## 7. Prepare the Application Code

Clone or copy into your project folder:
- `whisper_serve/` directory
- `serve_config.local.yaml`
- Load testing scripts (e.g., `load_test.py`)

Organize like:
```bash
/app
  |-- whisper_serve/
  |-- load_test.py
  |-- serve_config.local.yaml
  |-- requirements.txt
```


## 8. Start Ray and Deploy the App

Set the RAY environmental variables:
```
export RAY_DASHBOARD_ADDRESS=http://127.0.0.1:8265
export RAY_HEAD_ADDRESS=http://127.0.0.1:8265
```

Start Ray Serve head node:

```bash
ray start --head 
```

Then deploy your app:

```bash
serve deploy serve_config.local.yaml -a $RAY_DASHBOARD_ADDRESS
```

If running on GPU with 16GB the deployment is in two steps:
### Step 1
Comment out the whisper model to allow the llama model to load first:
```yaml
    deployments:
#      - name: WhisperTranscriber
#        num_replicas: 1
#        ray_actor_options:
#          num_cpus: 2
#          num_gpus: 0.5
      - name: Llama3Inference
        num_replicas: 1
        ray_actor_options:
          num_cpus: 2
          num_gpus: 0.5
```
Then deploy:
```bash
serve deploy serve_config.local.yaml -a $RAY_DASHBOARD_ADDRESS
```
### Step 1
Remove the comments:
```yaml
    deployments:
      - name: WhisperTranscriber
        num_replicas: 1
        ray_actor_options:
          num_cpus: 2
          num_gpus: 0.5
      - name: Llama3Inference
        num_replicas: 1
        ray_actor_options:
          num_cpus: 2
          num_gpus: 0.5
```
Then deploy:
```bash
serve deploy serve_config.local.yaml -a $RAY_DASHBOARD_ADDRESS
```

Monitor Ray Serve Dashboard:
- URL: http://localhost:8265


## 9. Run Load Tests

Once the app is live, from another terminal (remember to activate your env):

```bash
pyenv activate venv-3.9
cd tests
python combo_load_test.py
```

This will:
- Load test `/transcribe`
- Load test `/generate`
- Load test both mixed
- Plot concurrency vs latency graphs

## 10. To stop
```
serve shutdown -y -a $RAY_DASHBOARD_ADDRESS
ray stop --force
```
---

# 🌍 Ports Used

| Service | Port |
|:---|:---|
| Ray Serve HTTP API | 8000 |
| Ray Dashboard | 8265 |

Make sure firewall rules allow access if needed.

---

# 📊 Performance Tips

- Monitor GPU usage: `watch -n 1 nvidia-smi`
- Tune concurrency levels based on available VRAM
- Adjust `serve_config.local.yaml` for scaling replicas


---

# 🔧 Troubleshooting

| Issue | Possible Cause | Solution |
|:---|:---|:---|
| `torch.cuda.OutOfMemoryError` | Model too large or concurrency too high | Reduce concurrency, check batch sizes |
| `serve run` hangs | Wrong Ray version or Serve misconfiguration | Ensure Ray 2.43.0, validate config file |
| CUDA errors | Wrong torch wheel | Install correct `+cu121` wheels |
| Slow performance | CPU-bound inference | Confirm GPU inference enabled (nvidia-smi should show processes) |


---

# 🚀 Enjoy Full Whisper + Llama Serving with GPU Power!

---

(c) 2025 Graziano Labs Corp. All rights reserved.

