FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any are needed (e.g. build-essential for some pip packages, but slim is fine)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY agents/1_vision_mission/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy common library and install it in editable mode
COPY common /app/common
RUN pip install -e /app/common

# Copy agent source files
COPY agents/1_vision_mission/app.py /app/
COPY agents/1_vision_mission/agent.py /app/
COPY agents/1_vision_mission/logic.py /app/

# Expose Streamlit port
EXPOSE 8502

# Run command
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
