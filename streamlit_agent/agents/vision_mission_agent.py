import streamlit as st
import os
from agents.vision_mission_logic import (
    execute_agent_stream,
    save_result
)
from agents.graph_agent import run_document_refiner

CHAT_SYSTEM_PROMPT = """You are the Vision & Mission Chat Assistant. Your job is to help the user understand, refine, and update the 'vision_mission.md' file.
You have access to tools to read the current document, write updates to the document, and inspect other files in the workspace.
If the user asks you to change, add, or rewrite sections of the Vision, Mission, Values, or Brand Promise, use your tools to update the document, and then explain the updates you made.
Be professional, structured, and helpful."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div class="handoff-status handoff-ready">
                🟢 <strong>Handoff Status:</strong> Ready. This agent initiates the core brand identity.
            </div>
            """, unsafe_allow_html=True)
            
            industry = st.text_input("Industry / Sector", placeholder="e.g. FoodTech, AgriTech, FinTech...", key="vm_industry")
            audience = st.text_input("Primary Target Audience", placeholder="e.g. Office employees, health-conscious eaters...", key="vm_audience")
            principles = st.text_input("Brand Values / Principles", placeholder="e.g. Authenticity, health, hygiene, fair-trade...", key="vm_principles")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_vm_btn = st.button("✨ Execute Vision & Mission Agent", key="btn_exec_vm")
            
        if st.session_state.vision_mission_result:
            # 💬 Chat & Refine Section (ReAct Agent)
            st.markdown("---")
            st.markdown("### 💬 Chat & Refine Brand Identity")
            
            chat_container = st.container(height=350)
            with chat_container:
                if "vm_chat_history" not in st.session_state:
                    st.session_state.vm_chat_history = []
                for msg in st.session_state.vm_chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            
            chat_input = st.chat_input("Suggest changes, ask to rewrite, or Q&A about this document...", key="chat_input_vm")
            if chat_input:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                st.session_state.vm_chat_history.append({"role": "user", "content": chat_input})
                
                with st.chat_message("assistant"):
                    response = run_document_refiner(
                        chat_history=st.session_state.vm_chat_history[:-1],
                        user_message=chat_input,
                        project_folder=st.session_state.get("current_project", "default_project"),
                        target_doc="vision_mission.md",
                        agent_system_prompt=CHAT_SYSTEM_PROMPT,
                        selected_model=selected_model,
                        llm_engine=llm_engine,
                        server_host=server_host
                    )
                st.session_state.vm_chat_history.append({"role": "assistant", "content": response})
                
                # Reload document from disk to ensure UI is in sync
                from utils import get_docs_dir
                doc_path = os.path.join(get_docs_dir(), "vision_mission.md")
                if os.path.exists(doc_path):
                    with open(doc_path, "r", encoding="utf-8") as f:
                        st.session_state.vision_mission_result = f.read()
                        
                st.rerun()
        
    with col_out:
        if generate_vm_btn:
            if not st.session_state.shared_idea.strip():
                st.warning("⚠️ Please describe your Business Idea in the field above first.")
            else:
                st.session_state.vision_mission_result = ""
                with st.container(border=True):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        '<div class="agent-thinking">'
                        'Synthesizing Brand Identity'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    output_placeholder = st.empty()
                    
                    full_text = ""
                    try:
                        stream = execute_agent_stream(
                            shared_idea=st.session_state.shared_idea,
                            industry=industry,
                            audience=audience,
                            principles=principles,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        
                        st.session_state.vision_mission_result = full_text
                        save_result(full_text)
                        st.toast("✅ Automatically saved 'vision_mission.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.vision_mission_result:
            # 👁️ View / ✍️ Edit Mode Toggle
            edit_mode = st.toggle("✍️ Edit Document Manually", key="edit_mode_vm")
            
            if edit_mode:
                edited_text = st.text_area(
                    "Edit Vision & Mission Document", 
                    value=st.session_state.vision_mission_result, 
                    height=400, 
                    key="txt_edit_vm"
                )
                if st.button("💾 Save Changes", key="save_vm_manual", use_container_width=True):
                    save_result(edited_text)
                    st.session_state.vision_mission_result = edited_text
                    st.toast("✅ Manual edits saved successfully!")
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(st.session_state.vision_mission_result)
            
            col_dl, col_sav = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ Download as Markdown",
                    data=st.session_state.vision_mission_result,
                    file_name="vision_mission.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_vm"
                )
            with col_sav:
                if st.button("💾 Save to Shared Memory", key="sav_vm_btn", use_container_width=True):
                    save_result(st.session_state.vision_mission_result)
                    st.toast("✅ Saved 'vision_mission.md' to Shared Memory!")
                    st.rerun()
                    
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">🎯</div>
                <div class="title">Vision &amp; Mission Agent</div>
                <div class="sub">Click "Execute" on the left to synthesize the core identity.</div>
            </div>
            """, unsafe_allow_html=True)
