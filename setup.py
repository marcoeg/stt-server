from setuptools import setup, find_packages

setup(
    name="whisper_serve",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "ray[serve]",
        "openai-whisper",
        "fastapi",
        "python-multipart",
        "torch"
    ],
)