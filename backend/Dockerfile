# Pull official latest python Docker image
FROM --platform=linux/amd64 python:3.11.0

# Set working directory
WORKDIR /usr/backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/opt/venv

# Switch on virtual environment
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies
# RUN apt update

# Install python dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy all files
COPY . .

# Run the server
CMD fastapi dev src/main.py --host 0.0.0.0 --port 8001
# CMD uvicorn src.main:app --reload workers 4 --host 0.0.0.0 --port 8000

