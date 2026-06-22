import streamlit as st
from agents.architecture_logic import (
    check_handoff_status,
    execute_agent_stream,
    save_result
)
from agents.graph_agent import run_document_refiner

CHAT_SYSTEM_PROMPT = """You are the Technical Architecture Chat Assistant. Your job is to help the user understand, refine, and update the 'technical_architecture.md' file.
You have access to tools to read the current document, write updates to the document, and inspect other files in the workspace.
If the user asks you to modify the technical stack, database schemas, system architecture design, data flow, or security & compliance sections, use your tools to update the document, and then explain the updates you made.
Be professional, structured, and helpful."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            status_class, status_text = check_handoff_status()
            st.markdown(f"""
            <div class="handoff-status {status_class}">
                {status_text}
            </div>
            """, unsafe_allow_html=True)
            
            tech_pref = st.text_input("Tech Stack Preferences", placeholder="e.g. Python (FastAPI), React, Postgres, Supabase...", key="arch_tech")
            scale = st.text_input("Expected Traffic / User Base", placeholder="e.g. 100 orders/day at launch, up to 10k users/month in Year 1...", key="arch_scale")
            compliance = st.text_input("Compliance / Safety Needs", placeholder="e.g. Secure payment gateway integration, Indian DPDP compliance...", key="arch_compliance")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_arch_btn = st.button("✨ Execute Architecture Agent", key="btn_exec_arch")
            
        if st.session_state.architecture_result:
            # 💬 Chat & Refine Section (ReAct Agent)
            st.markdown("---")
            st.markdown("### 💬 Chat & Refine Technical Architecture")
            
            chat_container = st.container(height=350)
            with chat_container:
                if "arch_chat_history" not in st.session_state:
                    st.session_state.arch_chat_history = []
                for msg in st.session_state.arch_chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            
            chat_input = st.chat_input("Suggest changes, ask to rewrite, or Q&A about this document...", key="chat_input_arch")
            if chat_input:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                st.session_state.arch_chat_history.append({"role": "user", "content": chat_input})
                
                with st.chat_message("assistant"):
                    response = run_document_refiner(
                        chat_history=st.session_state.arch_chat_history[:-1],
                        user_message=chat_input,
                        project_folder=st.session_state.get("current_project", "default_project"),
                        target_doc="technical_architecture.md",
                        agent_system_prompt=CHAT_SYSTEM_PROMPT,
                        selected_model=selected_model,
                        llm_engine=llm_engine,
                        server_host=server_host
                    )
                st.session_state.arch_chat_history.append({"role": "assistant", "content": response})
                
                # Reload document from disk to ensure UI is in sync
                import os
                from utils import get_docs_dir
                doc_path = os.path.join(get_docs_dir(), "technical_architecture.md")
                if os.path.exists(doc_path):
                    with open(doc_path, "r", encoding="utf-8") as f:
                        st.session_state.architecture_result = f.read()
                        
                st.rerun()
        
    with col_out:
        if generate_arch_btn:
            if not st.session_state.shared_idea.strip():
                st.warning("⚠️ Please describe your Business Idea in the field above first.")
            else:
                st.session_state.architecture_result = ""
                with st.container(border=True):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        '<div class="agent-thinking">'
                        'Designing Technical Architecture Specification'
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
                            tech_pref=tech_pref,
                            scale=scale,
                            compliance=compliance,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        
                        st.session_state.architecture_result = full_text
                        save_result(full_text)
                        st.toast("✅ Automatically saved 'technical_architecture.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.architecture_result:
            # 👁️ View / ✍️ Edit Mode Toggle
            edit_mode = st.toggle("✍️ Edit Document Manually", key="edit_mode_arch")
            
            if edit_mode:
                edited_text = st.text_area(
                    "Edit Architecture Document", 
                    value=st.session_state.architecture_result, 
                    height=400, 
                    key="txt_edit_arch"
                )
                if st.button("💾 Save Changes", key="save_arch_manual", use_container_width=True):
                    save_result(edited_text)
                    st.session_state.architecture_result = edited_text
                    st.toast("✅ Manual edits saved successfully!")
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(st.session_state.architecture_result)
            
            col_dl, col_sav = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ Download as Markdown",
                    data=st.session_state.architecture_result,
                    file_name="technical_architecture.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_arch"
                )
            with col_sav:
                if st.button("💾 Save to Shared Memory", key="sav_arch_btn", use_container_width=True):
                    save_result(st.session_state.architecture_result)
                    st.toast("✅ Saved 'technical_architecture.md' to Shared Memory!")
                    st.rerun()
                    
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">🏗️</div>
                <div class="title">Architecture Agent</div>
                <div class="sub">Click "Execute" on the left to design a technical specification.</div>
            </div>
            """, unsafe_allow_html=True)
