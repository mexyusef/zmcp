"""
ZMCP Setup Script

Setup script for ZMCP package.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zmcp",
    version="0.0.1",
    author="Yusef Ulum",
    author_email="yusef314159@gmail.com",
    description="MCP Client/Server desktop app",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mexyusef/zmcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.0.0",
        "aiohttp>=3.8.0",
        "jsonschema>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "zmcp=zmcp.app:main",
        ],
    },
)
