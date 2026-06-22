FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY agents/3_requirements/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy common library and install it in editable mode
COPY common /app/common
RUN pip install -e /app/common

# Copy agent source files
COPY agents/3_requirements/app.py /app/
COPY agents/3_requirements/agent.py /app/
COPY agents/3_requirements/logic.py /app/

# Expose Streamlit port
EXPOSE 8504

# Run command
CMD ["streamlit", "run", "app.py", "--server.port=8504", "--server.address=0.0.0.0"]
