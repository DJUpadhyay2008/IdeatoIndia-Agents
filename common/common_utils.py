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
# Allow env override, and automatically fallback if host.docker.internal is not reachable.
def _detect_host():
    override = os.environ.get("LLM_HOST_OVERRIDE")
    if override:
        return override
        
    primary = "host.docker.internal" if IS_DOCKER else "localhost"
    secondary = "localhost" if IS_DOCKER else "127.0.0.1"
    
    # Try reaching Ollama (port 11434) or llama-server (port 8080) on primary host
    import socket
    for port in [11434, 8080]:
        try:
            socket.setdefaulttimeout(0.5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((primary, port))
            return primary
        except Exception:
            pass
            
    # If primary is not reachable but secondary is, use secondary
    for port in [11434, 8080]:
        try:
            socket.setdefaulttimeout(0.5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((secondary, port))
            return secondary
        except Exception:
            pass
            
    return primary

_HOST = _detect_host()

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
        
        # Skip index and summary duplicate files to optimize token usage
        if file == "document_index.json" or file.endswith(".summary.md"):
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

def strip_yaml_front_matter(content: str) -> str:
    if not content:
        return ""
    lines = content.strip().splitlines()
    if len(lines) > 2 and lines[0].strip() == "---":
        # Find the closing "---"
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return "\n".join(lines[idx+1:]).strip()
    return content.strip()

def save_document(name, content):
    docs_dir = get_docs_dir()
    name = "".join(c for c in name if c.isalnum() or c in ['.', '_', '-']).strip()
    if not name:
        name = "unnamed_doc.txt"
    path = os.path.join(docs_dir, name)
    
    cleaned_content = clean_markdown_document(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

def save_document_with_metadata(name, content, title, model=None, engine=None, host=None):
    """
    Saves document with extracted YAML front-matter, writes a separate *.summary.md asset,
    and updates the central document_index.json file.
    """
    docs_dir = get_docs_dir()
    name = "".join(c for c in name if c.isalnum() or c in ['.', '_', '-']).strip()
    if not name:
        name = "unnamed_doc.txt"
    path = os.path.join(docs_dir, name)
    
    cleaned_content = clean_markdown_document(content)
    
    # Initialize default metadata
    metadata = {
        "id": os.path.splitext(name)[0],
        "title": title,
        "summary_preview": "",
        "keywords": [],
        "entities": [],
        "related_sections": []
    }
    summary_content = ""
    
    if model and engine and host:
        # LLM prompt to extract metadata in JSON format
        system_prompt = (
            "You are an AI metadata extraction agent.\n"
            "Given a markdown document, your task is to extract:\n"
            "1. A bulleted list of 2-4 key summary points of the section.\n"
            "2. A list of key technological or architectural keywords (e.g. Python, Docker, Postgres, OAuth2).\n"
            "3. A list of specific tools, databases, or frameworks (entities) mentioned.\n"
            "4. A list of other sections/lenses that this section refers to or depends on. "
            "Select from: [summary, business, application, security, infrastructure, data].\n\n"
            "You must return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"summary_points\": [\"point 1\", \"point 2\"],\n"
            "  \"keywords\": [\"keyword 1\", \"keyword 2\"],\n"
            "  \"entities\": [\"entity 1\", \"entity 2\"],\n"
            "  \"related_sections\": [\"section_id 1\", \"section_id 2\"]\n"
            "}\n"
            "Do not include any extra text, explanations, or markdown code blocks. Return raw JSON text."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cleaned_content}
        ]
        
        try:
            response_text = ""
            for chunk in stream_chat(messages, model, engine, host):
                response_text += chunk
                
            clean_json_str = response_text.strip()
            if clean_json_str.startswith("```json"):
                clean_json_str = clean_json_str[7:]
            elif clean_json_str.startswith("```"):
                clean_json_str = clean_json_str[3:]
            if clean_json_str.endswith("```"):
                clean_json_str = clean_json_str[:-3]
            clean_json_str = clean_json_str.strip()
            
            extracted = json.loads(clean_json_str)
            summary_points = extracted.get("summary_points", [])
            metadata["keywords"] = extracted.get("keywords", [])
            metadata["entities"] = extracted.get("entities", [])
            metadata["related_sections"] = extracted.get("related_sections", [])
            
            if summary_points:
                summary_content = "\n".join(f"* {pt}" for pt in summary_points)
                metadata["summary_preview"] = ". ".join(summary_points[:2]) + "."
        except Exception as e:
            with open("agent_debug.log", "a", encoding="utf-8") as lf:
                lf.write(f"Metadata extraction failed for {name}: {e}\n")
                
    # Fallback if extraction was unsuccessful or not executed
    if not summary_content:
        lines = [l.strip() for l in cleaned_content.splitlines() if l.strip() and not l.strip().startswith("#")]
        preview = " ".join(lines[:2])
        if len(preview) > 200:
            preview = preview[:197] + "..."
        metadata["summary_preview"] = preview
        summary_content = f"* {preview}"
        
    # 1. Write the separate summary asset (*.summary.md)
    summary_name = name.replace(".md", ".summary.md")
    summary_path = os.path.join(docs_dir, summary_name)
    try:
        with open(summary_path, "w", encoding="utf-8") as sf:
            sf.write(summary_content)
    except Exception as e:
        with open("agent_debug.log", "a", encoding="utf-8") as lf:
            lf.write(f"Failed to write summary file: {e}\n")
            
    # 2. Add YAML Front-Matter to the main document file
    yaml_lines = [
        "---",
        f"id: {metadata['id']}",
        f"title: {metadata['title']}"
    ]
    if metadata["entities"]:
        yaml_lines.append(f"entities: {json.dumps(metadata['entities'])}")
    if metadata["keywords"]:
        yaml_lines.append(f"keywords: {json.dumps(metadata['keywords'])}")
    if metadata["related_sections"]:
        yaml_lines.append(f"related_sections: {json.dumps(metadata['related_sections'])}")
    yaml_lines.append("---")
    
    prepended_content = "\n".join(yaml_lines) + "\n\n" + cleaned_content
    with open(path, "w", encoding="utf-8") as f:
        f.write(prepended_content)
        
    # 3. Update the central document_index.json
    index_path = os.path.join(docs_dir, "document_index.json")
    index_data = {"project_id": os.path.basename(docs_dir), "sections": []}
    
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "sections" in loaded:
                    index_data = loaded
        except Exception:
            pass
            
    # Overwrite section record if it already exists
    index_data["sections"] = [s for s in index_data["sections"] if s.get("id") != metadata["id"]]
    index_data["sections"].append(metadata)
    
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)
    except Exception as e:
        with open("agent_debug.log", "a", encoding="utf-8") as lf:
            lf.write(f"Failed to update document_index.json: {e}\n")

def detect_intent_and_dependencies(user_message, docs_dir, model=None, engine=None, host=None):
    """
    Analyzes the user's edit request using the index to determine the target section and related sections.
    """
    index_path = os.path.join(docs_dir, "document_index.json")
    if not os.path.exists(index_path) or not model:
        return None
        
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    except Exception:
        return None
        
    sections = index_data.get("sections", [])
    if not sections:
        return None
        
    # Create a compact lookup structure for the model
    index_summary = []
    for s in sections:
        index_summary.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "keywords": s.get("keywords", []),
            "related_sections": s.get("related_sections", [])
        })
        
    system_prompt = (
        "You are an Intent Detection Agent.\n"
        "Your task is to identify which document section is the target of the user's modification request, "
        "and which other sections are related or dependent.\n\n"
        "Available sections:\n"
        f"{json.dumps(index_summary, indent=2)}\n\n"
        "You must return ONLY a JSON object matching this schema:\n"
        "{\n"
        "  \"target_section\": \"section_id or null\",\n"
        "  \"related_sections\": [\"section_id_1\", \"section_id_2\"]\n"
        "}\n"
        "Do not include any other text or explanation. Return raw JSON."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User Request: \"{user_message}\""}
    ]
    
    try:
        response_text = ""
        for chunk in stream_chat(messages, model, engine, host):
            response_text += chunk
            
        clean_json_str = response_text.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        elif clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()
        
        return json.loads(clean_json_str)
    except Exception as e:
        with open("agent_debug.log", "a", encoding="utf-8") as lf:
            lf.write(f"Intent detection failed: {e}\n")
        return None

def load_minimized_context(intent_result, docs_dir):
    """
    Resolves the minimized context based on intent analysis (Global summary, target content, and related summaries).
    """
    context_parts = []
    
    # 1. Global Summary (always load)
    global_sum_path = os.path.join(docs_dir, "architecture_summary.md")
    if os.path.exists(global_sum_path):
        try:
            with open(global_sum_path, "r", encoding="utf-8") as f:
                context_parts.append(f"=== GLOBAL DOCUMENT SUMMARY ===\n{f.read()}\n")
        except Exception:
            pass
            
    if not intent_result:
        return "\n".join(context_parts)
        
    target_id = intent_result.get("target_section")
    related_ids = intent_result.get("related_sections", [])
    
    # 2. Target Section (Full content)
    if target_id:
        target_file = None
        for f in os.listdir(docs_dir):
            if f.endswith(".md") and not f.endswith(".summary.md") and target_id in f:
                target_file = f
                break
        if target_file:
            try:
                with open(os.path.join(docs_dir, target_file), "r", encoding="utf-8") as f:
                    context_parts.append(f"=== ACTIVE TARGET SECTION ({target_file}) ===\n{f.read()}\n")
            except Exception:
                pass
                
    # 3. Related Section Summaries
    for rel_id in related_ids:
        if rel_id == target_id:
            continue
        rel_summary_file = None
        for f in os.listdir(docs_dir):
            if f.endswith(".summary.md") and rel_id in f:
                rel_summary_file = f
                break
        if rel_summary_file:
            try:
                with open(os.path.join(docs_dir, rel_summary_file), "r", encoding="utf-8") as f:
                    context_parts.append(f"=== RELATED SECTION SUMMARY ({rel_summary_file}) ===\n{f.read()}\n")
            except Exception:
                pass
                
    return "\n".join(context_parts)

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


def inject_premium_ui(active_step_num: int = 0):
    """Injects custom CSS styling and displays the horizontal steps navigation bar."""
    import streamlit as st
    
    # Define steps info
    steps = [
        {"name": "🏁 Cockpit", "port": 8501, "desc": "Dashboard"},
        {"name": "🎯 1: Vision", "port": 8502, "desc": "Vision & Mission"},
        {"name": "🔍 2: Research", "port": 8503, "desc": "Market Research"},
        {"name": "📋 3: Requirements", "port": 8504, "desc": "PRD Requirements"},
        {"name": "🏗️ 4: Architecture", "port": 8506, "desc": "Tech Architecture"},
        {"name": "📅 5: Planning", "port": 8505, "desc": "Launch Roadmap"}
    ]
    
    # CSS injection
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    /* Subtle Fade-in Entry Animations */
    @keyframes premiumFadeInUp {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .hero-card, .handoff-status, .pipeline-step, .empty-agent-state, 
    .agent-thinking, [data-testid="stExpander"], [data-testid="stMetric"], 
    [data-testid="stChatMessage"] {
        animation: premiumFadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    
    .premium-nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        padding: 10px 14px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        animation: premiumFadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    
    .premium-nav-steps {
        display: flex;
        gap: 8px;
        width: 100%;
        justify-content: space-between;
    }
    
    .premium-nav-item {
        flex: 1;
        text-align: center;
        padding: 8px 4px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        text-decoration: none !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        color: #64748b !important;
        border: 1px solid transparent;
        white-space: nowrap;
    }
    
    .premium-nav-item:hover {
        background-color: #f8fafc;
        color: #0f172a !important;
        border-color: #e2e8f0;
        transform: translateY(-1px);
    }
    
    .premium-nav-item.active {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        animation: activePulse 2s infinite alternate;
    }
    
    @keyframes activePulse {
        0% {
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }
        100% {
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.5);
            transform: scale(1.01);
        }
    }
    
    .hero-card {
        background: radial-gradient(circle at 100% 100%, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    .hero-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -10px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }
    
    .hero-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    
    .hero-subtitle {
        font-size: 0.95rem;
        color: #475569;
        line-height: 1.5;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background-color: #e2e8f0;
        color: #475569;
        position: relative;
        overflow: hidden;
    }
    
    .status-badge-ready {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    /* Subtle shimmering effect for step indicator badges */
    .status-badge-ready::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        animation: shimmerEffect 2.5s infinite;
    }
    
    @keyframes shimmerEffect {
        0% { left: -100%; }
        100% { left: 200%; }
    }
    
    /* Interactive custom buttons */
    .stButton > button {
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1.5px);
        box-shadow: 0 6px 16px -4px rgba(0, 0, 0, 0.1) !important;
        border-color: #cbd5e1 !important;
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    .empty-agent-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
        text-align: center;
        background-color: #f8fafc;
        border: 2px dashed #e2e8f0;
        border-radius: 16px;
        margin-top: 24px;
        transition: all 0.3s ease;
    }
    
    .empty-agent-state:hover {
        border-color: #cbd5e1;
        background-color: #f1f5f9;
    }
    
    .empty-agent-state .icon {
        font-size: 3rem;
        margin-bottom: 16px;
    }
    
    .empty-agent-state .title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 8px;
    }
    
    .empty-agent-state .sub {
        font-size: 0.9rem;
        color: #64748b;
        max-width: 400px;
    }
    
    .handoff-status {
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        background-color: #f8fafc;
        color: #475569;
        transition: all 0.3s ease;
    }
    
    .handoff-status.handoff-active {
        border-left: 4px solid #10b981;
        background-color: #f0fdf4;
        color: #14532d;
        font-weight: 600;
    }
    
    .handoff-status.handoff-ready {
        border-left: 4px solid #f59e0b;
        background-color: #fffbeb;
        color: #78350f;
        font-weight: 600;
    }
    
    .handoff-status.handoff-pending {
        border-left: 4px solid #e2e8f0;
        opacity: 0.6;
    }
    
    .pipeline-step {
        border-left: 4px solid #e2e8f0;
        padding: 14px;
        margin-bottom: 12px;
        background-color: #ffffff;
        border-radius: 4px 10px 10px 4px;
        border: 1px solid #e2e8f0;
        border-left-width: 4px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    .pipeline-step:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -8px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    
    .pipeline-step.complete {
        border-left-color: #10b981;
        background-color: #f0fdf4;
    }
    
    .pipeline-step.ready {
        border-left-color: #f59e0b;
        background-color: #fffbeb;
    }
    
    .pipeline-step.pending {
        border-left-color: #e2e8f0;
        opacity: 0.65;
    }
    
    .step-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .step-badge.complete {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .step-badge.ready {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    .step-badge.pending {
        background-color: #f3f4f6;
        color: #4b5563;
    }
    
    .section-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 8px;
    }
    
    .agent-thinking {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 12px 16px;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        color: #64748b;
        font-size: 0.9rem;
        font-style: italic;
    }
    
    .thinking-dot {
        width: 6px;
        height: 6px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        animation: thinking-bounce 1.4s infinite ease-in-out both;
    }
    
    .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
    .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes thinking-bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1.0); }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
    # Build steps HTML
    steps_html = '<div class="premium-nav-bar"><div class="premium-nav-steps">'
    for idx, s in enumerate(steps):
        is_active = (idx == active_step_num)
        active_class = " active" if is_active else ""
        steps_html += f'<a class="premium-nav-item{active_class}" id="nav-step-{idx}" href="http://localhost:{s["port"]}">{s["name"]}</a>'
    steps_html += '</div></div>'
    
    st.markdown(steps_html, unsafe_allow_html=True)


def render_premium_header_config(active_step_num: int = 1):
    """Renders a premium top horizontal configuration bar instead of a sidebar."""
    import streamlit as st
    from .common_utils import get_ollama_models, get_default_ollama_host, get_default_llm_host
    
    with st.container(border=True):
        st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#475569; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.05em;">⚙️ AI Workspace Engine Configuration</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        llm_engine_key = f"llm_engine_{active_step_num}"
        active_model_key = f"active_model_{active_step_num}"
        server_host_key = f"server_host_{active_step_num}"
        
        if llm_engine_key not in st.session_state:
            st.session_state[llm_engine_key] = "llama.cpp (llama-server)"
        if server_host_key not in st.session_state:
            st.session_state[server_host_key] = get_default_llm_host()
            
        with col1:
            llm_engine = st.selectbox(
                "LLM Engine", 
                ["Ollama", "llama.cpp (llama-server)", "Google Gemini API"], 
                key=llm_engine_key
            )
            
        with col2:
            if llm_engine == "Ollama":
                current_host = st.session_state.get(server_host_key, get_default_ollama_host())
                if "http" not in current_host:
                    current_host = get_default_ollama_host()
                available_models = get_ollama_models(current_host)
                sel_idx = 0
                prev_model = st.session_state.get(active_model_key)
                if prev_model in available_models:
                    sel_idx = available_models.index(prev_model)
                selected_model = st.selectbox("Active AI Model", available_models, index=sel_idx, key=active_model_key)
            elif llm_engine == "Google Gemini API":
                gemini_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
                sel_idx = 0
                prev_model = st.session_state.get(active_model_key)
                if prev_model in gemini_models:
                    sel_idx = gemini_models.index(prev_model)
                selected_model = st.selectbox("Active AI Model", gemini_models, index=sel_idx, key=active_model_key)
            else:
                selected_model = st.selectbox("Active AI Model", ["gemma4"], index=0, key=active_model_key)
                
        with col3:
            if llm_engine == "Ollama":
                host_val = st.text_input("Ollama Host URL", value=get_default_ollama_host(), key=server_host_key)
                server_host = host_val
            elif llm_engine == "Google Gemini API":
                gemini_api_key = st.text_input("Google Gemini API Key", type="password", value=st.session_state.get("gemini_api_key", ""))
                st.session_state.gemini_api_key = gemini_api_key
                server_host = ""
            else:
                host_val = st.text_input("llama.cpp Host URL", value=get_default_llm_host(), key=server_host_key)
                server_host = host_val
                
    return selected_model, llm_engine, server_host

