import os
import requests
import json
import pypdf

# Smart path detection for Docker vs local run
IS_DOCKER = os.path.exists("/app/documents")

if IS_DOCKER:
    DOCS_DIR = "/app/documents"
else:
    # Local fallback: streamlit_agent/documents in the project root
    # __file__ is common/common_utils.py, so go up 2 directories
    DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "streamlit_agent", "documents"))

# When running in Docker, localhost refers to the container itself.
# Use host.docker.internal to reach services on the host machine (llama-server, Ollama).
_HOST = "host.docker.internal" if IS_DOCKER else "localhost"

def get_default_llm_host() -> str:
    """Returns the correct llama.cpp server URL for the current runtime environment."""
    return f"http://{_HOST}:8080"

def get_default_ollama_host() -> str:
    """Returns the correct Ollama server URL for the current runtime environment."""
    return f"http://{_HOST}:11434"


def migrate_existing_files():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
    default_proj_dir = os.path.join(DOCS_DIR, "default_project")
    if not os.path.exists(default_proj_dir):
        os.makedirs(default_proj_dir)
    
    for item in os.listdir(DOCS_DIR):
        item_path = os.path.join(DOCS_DIR, item)
        if os.path.isfile(item_path):
            new_path = os.path.join(default_proj_dir, item)
            try:
                os.rename(item_path, new_path)
            except Exception:
                pass

def init_docs_dir():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
    migrate_existing_files()

def list_projects():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
    subdirs = [d for d in os.listdir(DOCS_DIR) if os.path.isdir(os.path.join(DOCS_DIR, d))]
    if "default_project" not in subdirs:
        subdirs.append("default_project")
    return sorted(subdirs)

def get_project_name_from_idea(idea):
    if not idea.strip():
        return "default_project"
    words = idea.strip().split()
    short_words = words[:4]
    title = "_".join(short_words).lower()
    clean_name = "".join(c for c in title if c.isalnum() or c == '_').strip('_')
    return clean_name if clean_name else "default_project"

def get_docs_dir():
    init_docs_dir()
    # Import streamlit dynamically to avoid issues in pure CLI environments
    try:
        import streamlit as st
        project = st.session_state.get("current_project", "default_project")
    except Exception:
        project = os.environ.get("CURRENT_PROJECT", "default_project")
        
    project_folder = "".join(c for c in project if c.isalnum() or c in ['_', '-']).strip()
    if not project_folder:
        project_folder = "default_project"
    
    path = os.path.join(DOCS_DIR, project_folder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def read_pdf(file_path):
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def load_shared_memory():
    docs_dir = get_docs_dir()
    files = os.listdir(docs_dir)
    if not files:
        return ""
    
    context_parts = []
    for file in sorted(files):
        path = os.path.join(docs_dir, file)
        if not os.path.isfile(path):
            continue
        
        ext = os.path.splitext(file)[1].lower()
        content = ""
        if ext in ['.txt', '.md', '.json', '.yaml', '.yml']:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading text file: {e}"
        elif ext == '.pdf':
            content = read_pdf(path)
        else:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                content = f"Unsupported file format or error: {e}"
        
        context_parts.append(f"--- START OF REFERENCE DOCUMENT: {file} ---\n{content}\n--- END OF REFERENCE DOCUMENT: {file} ---\n")
    
    return "\n".join(context_parts)

def clean_markdown_document(content: str) -> str:
    if not content:
        return ""
    
    lines = content.strip().splitlines()
    if lines and (lines[0].strip().startswith("```markdown") or lines[0].strip().startswith("```")):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
        
    text = "\n".join(lines).strip()
    
    first_header_idx = -1
    for marker in ["##", "#", "---"]:
        idx = text.find(marker)
        if idx != -1:
            if first_header_idx == -1 or idx < first_header_idx:
                first_header_idx = idx
                
    if first_header_idx > 0:
        preamble = text[:first_header_idx].strip()
        if len(preamble) < 300 and not any(line.strip().startswith("#") for line in preamble.splitlines()):
            text = text[first_header_idx:]
            
    return text.strip()

def save_document(name, content):
    docs_dir = get_docs_dir()
    name = "".join(c for c in name if c.isalnum() or c in ['.', '_', '-']).strip()
    if not name:
        name = "unnamed_doc.txt"
    path = os.path.join(docs_dir, name)
    
    cleaned_content = clean_markdown_document(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

def delete_document(name):
    docs_dir = get_docs_dir()
    path = os.path.join(docs_dir, name)
    if os.path.exists(path):
        os.remove(path)

def get_ollama_models(host="http://localhost:11434"):
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            if models:
                return models
    except Exception:
        pass
    return ["gemma4:e2b", "gemma4:e4b"]

def stream_chat(messages, model, engine="Ollama", host="http://localhost:11434"):
    if engine == "Ollama":
        url = f"{host}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode())
                        message = data.get("message", {})
                        chunk = message.get("content", "") if isinstance(message, dict) else ""
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama request failed: {exc}. Ensure Ollama is running.")
            
    elif engine == "Google Gemini API":
        try:
            import streamlit as st
            api_key = st.session_state.get("gemini_api_key", "").strip()
        except Exception:
            api_key = ""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Google Gemini API Key is missing. Please enter it in the sidebar or set the GEMINI_API_KEY environment variable.")
        
        gemini_contents = []
        system_instruction = None
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instruction = {
                    "parts": [{"text": content}]
                }
            elif role == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role in ["assistant", "model"]:
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
        payload = {
            "contents": gemini_contents
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
            
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode().strip()
                    if line_str.startswith("data: "):
                        data_content = line_str[6:]
                        try:
                            data = json.loads(data_content)
                            candidates = data.get("candidates", [])
                            if candidates:
                                content_obj = candidates[0].get("content", {})
                                parts = content_obj.get("parts", [])
                                if parts:
                                    chunk = parts[0].get("text", "")
                                    if chunk:
                                        yield chunk
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException as exc:
            raise RuntimeError(f"Gemini API request failed: {exc}. Please check your API key and network connection.")
    else:
        url = f"{host}/v1/chat/completions"
        payload = {
            "messages": messages,
            "stream": True,
            "model": model,
        }
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode().strip()
                    if line_str.startswith("data: "):
                        data_content = line_str[6:]
                        if data_content == "[DONE]":
                            break
                        try:
                            data = json.loads(data_content)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    yield chunk
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException as exc:
            raise RuntimeError(f"llama-server request failed: {exc}. Ensure llama-server is running on {host}.")
