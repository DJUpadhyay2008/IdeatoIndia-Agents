# 📚 Streamlit LLM Chat Agent

## Overview

A **premium‑looking** Streamlit application that acts as a middleware UI for a locally‑hosted LLM via **Ollama**.  It provides:
- Glass‑morphism styling with dark‑mode support.
- Real‑time streaming responses from the model.
- Conversation history persisted in the Streamlit session.
- Easy‑to‑change model configuration.

The repo lives under `/home/dutt/IdeaToIndia/streamlit_agent`.

---

## Quick Start

```bash
# 1️⃣ Clone / navigate to the project folder
cd /home/dutt/IdeaToIndia/streamlit_agent

# 2️⃣ (Optional) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3️⃣ Install Python dependencies
pip install -r requirements.txt

# 4️⃣ Make sure Ollama is running and the model is available
ollama serve                # starts the HTTP server on 127.0.0.1:11434
ollama pull gemma4:e2b       # or any other model you want to use

# 5️⃣ Launch the Streamlit UI
streamlit run app.py
```

Open the URL printed by Streamlit (normally `http://localhost:8501`). You should see a sleek chat window ready to talk to your local model.

---

## Configuration

Edit the top of `app.py` if you need to point to a different Ollama endpoint or use another model:
```python
OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma4:e2b"   # change to your preferred model name
```

---

## Docker (optional)

If you prefer containerised execution, a simple Dockerfile is provided. Build and run with:
```bash
docker build -t streamlit-llm-agent .
docker run -p 8501:8501 streamlit-llm-agent
```
> **Note**: The container expects an external Ollama server reachable at `host.docker.internal:11434`. Adjust the `OLLAMA_ENDPOINT` environment variable if needed.

---

## Project Structure

```
streamlit_agent/
│─ app.py                # Streamlit UI + Ollama integration
│─ requirements.txt      # Python dependencies
│─ Dockerfile            # Optional container definition
│─ .gitignore            # Ignored files for version control
│─ README.md             # <-- you are reading it!
```

---

## License

MIT License – feel free to use, modify, and share.

---

## Contributing

1. Fork the repo.
2. Create a feature branch.
3. Submit a Pull Request with a clear description of the change.
4. Ensure the UI remains premium (keep the glass‑morphism theme, animations, and dark‑mode support).

---

## Troubleshooting

- **`Error: Ollama request failed`** – Verify that Ollama is running, the port is correct, and the model name exists (`ollama list`).
- **No response streaming** – Ensure your Python `requests` version is ≥ 2.32 (already pinned) and that the server returns `Transfer‑Encoding: chunked`.
- **UI looks broken** – The custom CSS is injected via `st.markdown`. If you edit it, keep the `--bg-gradient`, `--card-bg`, and `backdrop-filter` rules for the premium look.

---

Enjoy chatting with your own LLM! 🚀
