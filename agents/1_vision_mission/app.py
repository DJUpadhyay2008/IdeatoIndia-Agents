# Standalone runner for the Vision & Mission Agent
import streamlit as st
import os
import sys

# Import from common package and local agent
from common import (
    init_docs_dir,
    read_pdf,
    load_shared_memory,
    save_document,
    delete_document,
    get_ollama_models,
    stream_chat,
    get_docs_dir,
    list_projects,
    get_project_name_from_idea,
    get_default_llm_host,
    get_default_ollama_host,
)
import agent

# Initialize shared documents directory
init_docs_dir()

# Set Page Config
st.set_page_config(
    page_title="IdeaToIndia — Standalone Vision & Mission Agent",
    page_icon="🎯",
    layout="wide",
)

# ---------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------
if "current_project" not in st.session_state:
    st.session_state.current_project = "default_project"
if "shared_idea" not in st.session_state:
    st.session_state.shared_idea = ""
if "vision_mission_result" not in st.session_state:
    st.session_state.vision_mission_result = ""

def load_project_state():
    proj_dir = get_docs_dir()
    file_map = {
        "vision_mission.md": "vision_mission_result",
        "market_research.md": "research_result",
        "prd_requirements.md": "requirements_result",
        "launch_plan.md": "planning_result",
        "technical_architecture.md": "architecture_result",
        "business_idea.txt": "shared_idea"
    }
    for var in file_map.values():
        st.session_state[var] = ""
    for filename, varname in file_map.items():
        filepath = os.path.join(proj_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    st.session_state[varname] = f.read()
            except Exception:
                pass

if "vision_mission_result" not in st.session_state or not st.session_state.vision_mission_result:
    load_project_state()

# ---------------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------------
st.markdown("""
<div style="background: radial-gradient(circle at 50% 30%, #fef2f2 0%, #fff1f2 50%, #fffbeb 100%); padding: 2rem; border-radius: 16px; border: 1px solid #e2e8f0; margin-bottom: 2rem; text-align: center;">
    <div style="font-weight: 800; font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; color: #e11d48; margin-bottom: 0.5rem;">🎯 IdeaToIndia Standalone Agent</div>
    <div style="font-size: 2.2rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem; font-family: 'Playfair Display', serif;">Vision &amp; Mission Identity</div>
    <div style="color: #475569; font-size: 0.95rem; max-width: 600px; margin: 0 auto;">
        Establish the core values, long-term vision, target audience, and brand promise of your startup idea.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Sidebar: Project Workspace, Settings & Shared Memory
# ---------------------------------------------------------------
st.sidebar.markdown('### 📁 Project Workspace')

# List projects dynamically
projects = list_projects()
try:
    proj_index = projects.index(st.session_state.current_project)
except ValueError:
    proj_index = 0

selected_proj = st.sidebar.selectbox("Active Project Folder", projects, index=proj_index)
if selected_proj != st.session_state.current_project:
    st.session_state.current_project = selected_proj
    load_project_state()
    st.rerun()

st.sidebar.markdown('---')
st.sidebar.markdown('### ⚙️ Workspace Settings')

# Engine & Model selection (Defaults to llama-server on GPU)
llm_engine = st.sidebar.selectbox("LLM Engine", ["Ollama", "llama.cpp (llama-server)", "Google Gemini API"], index=1)

if llm_engine == "Ollama":
    available_models = get_ollama_models(get_default_ollama_host())
    selected_model = st.sidebar.selectbox("Active AI Model", available_models, index=0)
    server_host = st.sidebar.text_input("Ollama Host URL", value=get_default_ollama_host())
elif llm_engine == "Google Gemini API":
    gemini_api_key = st.sidebar.text_input("Google Gemini API Key", type="password", value=st.session_state.get("gemini_api_key", ""))
    st.session_state.gemini_api_key = gemini_api_key
    selected_model = st.sidebar.selectbox(
        "Active AI Model", 
        ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
        index=0
    )
    server_host = ""
else:
    selected_model = "gemma4"  # llama-server uses pre-loaded model
    server_host = st.sidebar.text_input("llama.cpp Host URL", value=get_default_llm_host())

st.sidebar.markdown('---')
st.sidebar.markdown('### 📁 Shared Memory (Documents)')

# Document manager listing files
files = os.listdir(get_docs_dir())
if not files:
    st.sidebar.info("Shared memory is currently empty. Prior documents will load here once available.")
else:
    st.sidebar.markdown(f"**Files in Memory ({len(files)}):**")
    for file in sorted(files):
        with st.sidebar.expander(f"📄 {file}", expanded=False):
            path = os.path.join(get_docs_dir(), file)
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.txt', '.md', '.json']:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        st.text(f.read()[:600] + ("..." if len(f.read()) > 600 else ""))
                except Exception as e:
                    st.error(f"Error: {e}")
            elif ext == '.pdf':
                pdf_text = read_pdf(path)
                st.text(pdf_text[:600] + ("..." if len(pdf_text) > 600 else ""))

# ---------------------------------------------------------------
# Core Business Idea (Shared)
# ---------------------------------------------------------------
with st.container(border=True):
    st.markdown('### 💡 Shared Business Idea')
    shared_idea = st.text_area(
        "Describe your core business idea (automatically shared with the Vision & Mission Agent)",
        value=st.session_state.shared_idea,
        placeholder="e.g. A localized food delivery platform in India that connects home-cooked meal creators (home chefs) directly with corporate professionals seeking healthy lunches.",
        height=80,
    )
    if shared_idea != st.session_state.shared_idea:
        st.session_state.shared_idea = shared_idea
        
        new_proj = get_project_name_from_idea(shared_idea)
        if new_proj != st.session_state.current_project:
            st.session_state.current_project = new_proj
            proj_dir = get_docs_dir()
            idea_path = os.path.join(proj_dir, "business_idea.txt")
            with open(idea_path, "w", encoding="utf-8") as f:
                f.write(shared_idea)
            load_project_state()
            st.session_state.shared_idea = shared_idea
            st.toast(f"📁 Switched to project: {new_proj}")
            st.rerun()
        else:
            proj_dir = get_docs_dir()
            idea_path = os.path.join(proj_dir, "business_idea.txt")
            with open(idea_path, "w", encoding="utf-8") as f:
                f.write(shared_idea)

# ---------------------------------------------------------------
# Render standalone Vision & Mission Agent
# ---------------------------------------------------------------
agent.render(selected_model, llm_engine, server_host)
