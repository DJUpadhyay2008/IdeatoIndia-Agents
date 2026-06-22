FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY agents/2_research/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy common library and install it in editable mode
COPY common /app/common
RUN pip install -e /app/common

# Copy agent source files
COPY agents/2_research/app.py /app/
COPY agents/2_research/agent.py /app/
COPY agents/2_research/logic.py /app/

# Expose Streamlit port
EXPOSE 8503

# Run command
CMD ["streamlit", "run", "app.py", "--server.port=8503", "--server.address=0.0.0.0"]
