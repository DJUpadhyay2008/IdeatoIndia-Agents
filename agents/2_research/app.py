# Standalone runner for the Research Agent
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
    inject_premium_ui,
    render_premium_header_config,
    strip_yaml_front_matter,
)
import agent

# Initialize shared documents directory
init_docs_dir()

# Set Page Config
st.set_page_config(
    page_title="IdeaToIndia — Standalone Research & Discovery Agent",
    page_icon="🔍",
    layout="wide",
)

# Inject Premium UI & Steps Progress Tracker
inject_premium_ui(2)

# ---------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------
if "current_project" not in st.session_state:
    st.session_state.current_project = "default_project"
if "shared_idea" not in st.session_state:
    st.session_state.shared_idea = ""
if "research_result" not in st.session_state:
    st.session_state.research_result = ""

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
                    content = f.read()
                    if filename.endswith(".md"):
                        content = strip_yaml_front_matter(content)
                    st.session_state[varname] = content
            except Exception:
                pass

if "research_result" not in st.session_state or not st.session_state.research_result:
    load_project_state()

# ---------------------------------------------------------------
# Hero Section
# ---------------------------------------------------------------
st.markdown("""
<div class="hero-card">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <span class="status-badge status-badge-ready">🟢 Step 2 of 5</span>
        <span style="font-size: 0.8rem; color: #6B7280; font-weight: 500;">Market Research &amp; Discovery</span>
    </div>
    <div class="hero-title">Market Research &amp; Discovery</div>
    <div class="hero-subtitle">Perform market landscape mapping, identify direct/indirect competitors, target regions, and define your Go-To-Market strategy.</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Header Configuration
# ---------------------------------------------------------------
selected_model, llm_engine, server_host = render_premium_header_config(2)

# ---------------------------------------------------------------
# Core Business Idea (Shared)
# ---------------------------------------------------------------
with st.container(border=True):
    idea_card_html = """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #4B5563; text-transform: uppercase; letter-spacing: 0.05em;">💡 Core Business Idea</div>
        <div style="font-size: 0.8rem; color: #10B981; display: flex; align-items: center; gap: 4px;">
            <span style="font-size: 10px;">●</span> Autosaved to memory
        </div>
    </div>
    """
    st.markdown(idea_card_html, unsafe_allow_html=True)
    
    shared_idea = st.text_area(
        "Describe your core business idea (automatically shared with the Research Agent)",
        value=st.session_state.shared_idea,
        placeholder="e.g. A localized food delivery platform in India that connects home-cooked meal creators (home chefs) directly with corporate professionals seeking healthy lunches.",
        height=100,
        label_visibility="collapsed"
    )
    char_count = len(shared_idea)
    st.markdown(f'<div style="text-align: right; font-size: 0.75rem; color: #9CA3AF; margin-top: -8px;">{char_count} characters</div>', unsafe_allow_html=True)

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
# Render standalone Research Agent
# ---------------------------------------------------------------
agent.render(selected_model, llm_engine, server_host)
