# Use Python 3.10 slim as base image
FROM python:3.10-slim

# install tesseract and other dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    tesseract-ocr-eng \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# set working directory
WORKDIR /code

# copy requirements.txt to the working directory
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy whole project to the working directory
COPY . .

# run app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5500", "app.app:app"]