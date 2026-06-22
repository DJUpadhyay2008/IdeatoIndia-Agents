import streamlit as st
import os
import sys

# Support importing common package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import from common package
from common import (
    init_docs_dir,
    read_pdf,
    load_shared_memory,
    save_document,
    get_docs_dir,
    list_projects,
    get_project_name_from_idea,
    SupervisorAgent,
    stream_chat,
    get_default_llm_host,
    get_default_ollama_host,
)

# Initialize shared documents directory
init_docs_dir()

# Set Page Config
st.set_page_config(
    page_title="IdeaToIndia — Master Strategy Cockpit",
    page_icon="🇮🇳",
    layout="wide",
)

# ---------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------
if "current_project" not in st.session_state:
    st.session_state.current_project = "default_project"
if "shared_idea" not in st.session_state:
    st.session_state.shared_idea = ""
if "audit_report" not in st.session_state:
    st.session_state.audit_report = ""
if "dashboard_chat_history" not in st.session_state:
    st.session_state.dashboard_chat_history = []

def load_project_state():
    proj_dir = get_docs_dir()
    idea_path = os.path.join(proj_dir, "business_idea.txt")
    if os.path.exists(idea_path):
        try:
            with open(idea_path, "r", encoding="utf-8") as f:
                st.session_state.shared_idea = f.read()
        except Exception:
            pass
    else:
        st.session_state.shared_idea = ""
    # Reset audit report on project switch
    st.session_state.audit_report = ""
    st.session_state.dashboard_chat_history = []

if "shared_idea" not in st.session_state or not st.session_state.shared_idea:
    load_project_state()

# ---------------------------------------------------------------
# Style Injection
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');

html, body, p, span, label, input, textarea, select, button, div, li, a {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Pipeline visualization card */
.pipeline-step {
    border-left: 5px solid #cbd5e1;
    padding: 1rem;
    margin-bottom: 0.75rem;
    background-color: #ffffff;
    border-radius: 4px 12px 12px 4px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    transition: all 0.2s ease;
}
.pipeline-step.complete {
    border-left-color: #10b981;
}
.pipeline-step.ready {
    border-left-color: #f59e0b;
}
.pipeline-step.pending {
    border-left-color: #cbd5e1;
    opacity: 0.65;
}

.step-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
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
    background-color: #f1f5f9;
    color: #475569;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------------
st.markdown("""
<div style="background: radial-gradient(circle at 50% 30%, #f0fdf4 0%, #e0f2fe 50%, #fffbeb 100%); padding: 2.5rem 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0; margin-bottom: 2rem; text-align: center;">
    <div style="font-weight: 800; font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; color: #0284c7; margin-bottom: 0.5rem;">🇮🇳 Multi-Agent Startup Orchestrator</div>
    <div style="font-size: 2.4rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem; font-family: 'Playfair Display', serif;">Strategy Agent Dashboard</div>
    <div style="color: #475569; font-size: 0.98rem; max-width: 650px; margin: 0 auto; line-height: 1.6;">
        Coordinate requirements, system designs, market audits, and launch plans across your modular strategy microservices.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
st.sidebar.markdown('### 📁 Active Project Workspace')
projects = list_projects()
try:
    proj_index = projects.index(st.session_state.current_project)
except ValueError:
    proj_index = 0

selected_proj = st.sidebar.selectbox("Project Folder", projects, index=proj_index)
if selected_proj != st.session_state.current_project:
    st.session_state.current_project = selected_proj
    load_project_state()
    st.rerun()

st.sidebar.markdown('---')
st.sidebar.markdown('### ⚙️ Engine Configurations')
llm_engine = st.sidebar.selectbox("LLM Engine", ["Ollama", "llama.cpp (llama-server)", "Google Gemini API"], index=1)

if llm_engine == "Ollama":
    selected_model = "gemma4:e2b"
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
    selected_model = "gemma4"
    server_host = st.sidebar.text_input("llama.cpp Host URL", value=get_default_llm_host())

st.sidebar.markdown('---')
st.sidebar.markdown('### 📁 Shared Memory (Documents)')
files = os.listdir(get_docs_dir())
if not files:
    st.sidebar.info("Shared memory is empty.")
else:
    for file in sorted(files):
        with st.sidebar.expander(f"📄 {file}", expanded=False):
            path = os.path.join(get_docs_dir(), file)
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.txt', '.md', '.json']:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        st.text(f.read()[:500] + ("..." if len(f.read()) > 500 else ""))
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------------------------------------------------------
# Main Layout
# ---------------------------------------------------------------
col_left, col_right = st.columns([1, 1.2])

with col_left:
    with st.container(border=True):
        st.markdown('### 💡 Core Business Idea')
        shared_idea = st.text_area(
            "Define the startup / business idea:",
            value=st.session_state.shared_idea,
            placeholder="Describe your idea here...",
            height=100
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

    # 🚦 Pipeline Handoff Status Board
    with st.container(border=True):
        st.markdown('### 🚦 Strategy Pipeline Status')
        
        status = SupervisorAgent.get_pipeline_status(st.session_state.current_project)
        
        # Display Step 1: Vision & Mission
        vm = status["1_vision_mission"]
        if vm["exists"]:
            st.markdown("""
            <div class="pipeline-step complete">
                <strong>🎯 Step 1: Vision & Mission</strong><br>
                File: <code>vision_mission.md</code> <span class="step-badge complete">Complete</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pipeline-step {'ready' if vm['ready_to_execute'] else 'pending'}">
                <strong>🎯 Step 1: Vision & Mission</strong><br>
                File: <code>vision_mission.md</code> 
                <span class="step-badge {'ready' if vm['ready_to_execute'] else 'pending'}">
                    {'Ready to Run' if vm['ready_to_execute'] else 'Pending Idea'}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
        # Display Step 2: Research
        res = status["2_research"]
        if res["exists"]:
            st.markdown("""
            <div class="pipeline-step complete">
                <strong>🔍 Step 2: Market Research</strong><br>
                File: <code>market_research.md</code> <span class="step-badge complete">Complete</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pipeline-step {'ready' if res['ready_to_execute'] else 'pending'}">
                <strong>🔍 Step 2: Market Research</strong><br>
                File: <code>market_research.md</code> 
                <span class="step-badge {'ready' if res['ready_to_execute'] else 'pending'}">
                    {'Ready to Run' if res['ready_to_execute'] else 'Pending Step 1'}
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Display Step 3: Requirements
        req = status["3_requirements"]
        if req["exists"]:
            st.markdown("""
            <div class="pipeline-step complete">
                <strong>📋 Step 3: Requirements (PRD)</strong><br>
                File: <code>prd_requirements.md</code> <span class="step-badge complete">Complete</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pipeline-step {'ready' if req['ready_to_execute'] else 'pending'}">
                <strong>📋 Step 3: Requirements (PRD)</strong><br>
                File: <code>prd_requirements.md</code> 
                <span class="step-badge {'ready' if req['ready_to_execute'] else 'pending'}">
                    {'Ready to Run' if req['ready_to_execute'] else 'Pending Step 2'}
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Display Step 4: Architecture
        arch = status["5_architecture"]
        if arch["exists"]:
            st.markdown("""
            <div class="pipeline-step complete">
                <strong>🏗️ Step 4: Technical Architecture</strong><br>
                File: <code>technical_architecture.md</code> <span class="step-badge complete">Complete</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pipeline-step {'ready' if arch['ready_to_execute'] else 'pending'}">
                <strong>🏗️ Step 4: Technical Architecture</strong><br>
                File: <code>technical_architecture.md</code> 
                <span class="step-badge {'ready' if arch['ready_to_execute'] else 'pending'}">
                    {'Ready to Run' if arch['ready_to_execute'] else 'Pending Step 3'}
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Display Step 5: Planning
        plan = status["4_planning"]
        if plan["exists"]:
            st.markdown("""
            <div class="pipeline-step complete">
                <strong>📅 Step 5: Launch Plan & Checklist</strong><br>
                File: <code>launch_plan.md</code> <span class="step-badge complete">Complete</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pipeline-step {'ready' if plan['ready_to_execute'] else 'pending'}">
                <strong>📅 Step 5: Launch Plan & Checklist</strong><br>
                File: <code>launch_plan.md</code> 
                <span class="step-badge {'ready' if plan['ready_to_execute'] else 'pending'}">
                    {'Ready to Run' if plan['ready_to_execute'] else 'Pending Step 4'}
                </span>
            </div>
            """, unsafe_allow_html=True)

    # 🔗 Microservice Gateways
    with st.container(border=True):
        st.markdown('### 🔗 Microservice Shortcuts')
        st.markdown("""
        Access individual agent interfaces to edit or refine documents:
        - [🎯 Vision & Mission Agent](http://localhost:8502)
        - [🔍 Market Research Agent](http://localhost:8503)
        - [📋 Requirements Agent](http://localhost:8504)
        - [📅 Planning Agent](http://localhost:8505)
        - [🏗️ Architecture Agent](http://localhost:8506)
        """)

with col_right:
    # 🔍 Consistency Audit Card
    with st.container(border=True):
        st.markdown('### 🔍 Pipeline Consistency Audit')
        st.markdown('Scan all generated strategy documents to audit logical flow, contradictions, and strategic alignment.')
        
        audit_btn = st.button("🔍 Execute Consistency Audit", use_container_width=True)
        if audit_btn:
            audit_placeholder = st.empty()
            full_audit = ""
            for chunk in SupervisorAgent.run_consistency_audit(selected_model, llm_engine, server_host, st.session_state.current_project):
                full_audit += chunk
                audit_placeholder.markdown(full_audit)
            st.session_state.audit_report = full_audit
        elif st.session_state.audit_report:
            st.markdown(st.session_state.audit_report)

    # 💬 Harness Q&A Chat Advisor
    with st.container(border=True):
        st.markdown('### 💬 Central Strategy Chat Advisor')
        
        chat_container = st.container(height=350)
        with chat_container:
            for msg in st.session_state.dashboard_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        chat_input = st.chat_input("Ask about any document or overall startup strategy...", key="dashboard_chat_in")
        if chat_input:
            with st.chat_message("user"):
                st.markdown(chat_input)
            st.session_state.dashboard_chat_history.append({"role": "user", "content": chat_input})
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                bot_reply = ""
                
                # Fetch memory context
                memory_ctx = load_shared_memory()
                
                # Construct chat advisor message flow
                chat_messages = [
                    {"role": "system", "content": "You are the Master AI Strategy Advisor. You have context over all strategic documents generated for this startup. Help the user reconcile planning discrepancies, explain technical choices, or brainstorm strategy based on these files."}
                ]
                if memory_ctx:
                    chat_messages.append({"role": "system", "content": f"Here is the contents of the Shared Memory folder for reference:\n{memory_ctx}"})
                if st.session_state.shared_idea.strip():
                    chat_messages.append({"role": "system", "content": f"The core startup idea is: {st.session_state.shared_idea.strip()}"})
                    
                chat_messages.extend(st.session_state.dashboard_chat_history)
                
                try:
                    for chunk in stream_chat(chat_messages, selected_model, llm_engine, server_host):
                        bot_reply += chunk
                        placeholder.markdown(bot_reply)
                    st.session_state.dashboard_chat_history.append({"role": "assistant", "content": bot_reply})
                except Exception as e:
                    placeholder.error(f"Error: {e}")
            st.rerun()
