FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY agents/5_architecture/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy common library and install it in editable mode
COPY common /app/common
RUN pip install -e /app/common

# Copy agent source files
COPY agents/5_architecture/app.py /app/
COPY agents/5_architecture/agent.py /app/
COPY agents/5_architecture/logic.py /app/

# Copy externalized subagent prompts/skills/instructions
COPY agents/5_architecture/subagents /app/subagents


# Expose Streamlit port
EXPOSE 8506

# Run command
CMD ["streamlit", "run", "app.py", "--server.port=8506", "--server.address=0.0.0.0"]
