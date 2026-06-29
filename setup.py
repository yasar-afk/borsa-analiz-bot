from setuptools import setup, find_packages

with open("README.txt", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="borsa-analiz-bot",
    version="1.0.0",
    author="yasar-afk",
    description="AI destekli borsa analiz ve trading botu",
    long_description=long_description,
    long_description_content_type="text/plain",
    url="https://github.com/yasar-afk/borsa-analiz-bot",
    py_modules=["live_v7", "config"],
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "borsa-bot=live_v7:main",
        ],
    },
)
