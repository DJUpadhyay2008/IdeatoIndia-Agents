import os
import requests
import json
import pypdf
import streamlit as st

OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")

def migrate_existing_files():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    default_proj_dir = os.path.join(base_dir, "default_project")
    if not os.path.exists(default_proj_dir):
        os.makedirs(default_proj_dir)
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isfile(item_path):
            new_path = os.path.join(default_proj_dir, item)
            try:
                os.rename(item_path, new_path)
            except Exception:
                pass

def init_docs_dir():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    migrate_existing_files()

init_docs_dir()

def list_projects():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
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
    try:
        project = st.session_state.get("current_project", "default_project")
    except Exception:
        project = os.environ.get("CURRENT_PROJECT", "default_project")
    project_folder = "".join(c for c in project if c.isalnum() or c in ['_', '-']).strip()
    if not project_folder:
        project_folder = "default_project"
    
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents", project_folder)
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

def save_document(name, content):
    docs_dir = get_docs_dir()
    name = "".join(c for c in name if c.isalnum() or c in ['.', '_', '-']).strip()
    if not name:
        name = "unnamed_doc.txt"
    path = os.path.join(docs_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def delete_document(name):
    docs_dir = get_docs_dir()
    path = os.path.join(docs_dir, name)
    if os.path.exists(path):
        os.remove(path)

@st.cache_data(show_spinner=False)
def get_ollama_models():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
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
