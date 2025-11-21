"""
Setup configuration for Call Center AI Local
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="call-center-ai-local",
    version="1.0.0",
    author="Your Organization",
    author_email="support@yourorg.com",
    description="Production-ready, on-premise AI-powered call center solution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/call-center-ai-local",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Telephony",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=8.3.4",
            "pytest-asyncio>=0.25.1",
            "pytest-cov>=6.0.0",
            "black>=24.10.0",
            "flake8>=7.1.1",
            "mypy>=1.14.1",
            "pre-commit>=3.5.0",
        ],
        "gpu": [
            "torch>=2.0.0+cu118",
            "accelerate>=0.25.0",
            "bitsandbytes>=0.41.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "call-center-ai=app.main:main",
        ],
    },
    package_data={
        "app": ["*.yaml", "*.yml", "*.json"],
    },
    include_package_data=True,
)
