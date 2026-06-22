import streamlit as st
from agents.requirements_logic import (
    get_handoff_files_present,
    execute_agent_stream,
    save_result
)
from agents.graph_agent import run_document_refiner

CHAT_SYSTEM_PROMPT = """You are the Product Requirements Document (PRD) Chat Assistant. Your job is to help the user understand, refine, and update the 'prd_requirements.md' file.
You have access to tools to read the current document, write updates to the document, and inspect other files in the workspace.
If the user asks you to modify sections of the functional/non-functional requirements, add new features, adjust user roles/personas, or update acceptance criteria, use your tools to update the document, and then explain the updates you made.
Be professional, structured, and helpful."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            has_vm, has_res = get_handoff_files_present()
            
            if has_vm and has_res:
                st.markdown("""
                <div class="handoff-status handoff-active">
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>vision_mission.md</code> and <code>market_research.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            elif has_vm or has_res:
                loaded_file = "vision_mission.md" if has_vm else "market_research.md"
                missing_file = "market_research.md" if has_vm else "vision_mission.md"
                st.markdown(f"""
                <div class="handoff-status handoff-pending">
                    ⚠️ <strong>Partial Handoff:</strong> Loaded <code>{loaded_file}</code>. Missing <code>{missing_file}</code>. We recommend running all previous agents first.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="handoff-status handoff-pending">
                    ⚠️ <strong>Handoff Pending:</strong> No prior files detected. Run Vision/Mission and Market Research agents first for aligned product scope.
                </div>
                """, unsafe_allow_html=True)
                
            target_roles = st.text_input("User Roles / Persona Types", placeholder="e.g. Job Seeker, Recruiter, Admin...", key="req_roles")
            key_features = st.text_area("Key Features / Modules (e.g. MVP Scope)", placeholder="e.g. Candidate registration, CV parsing, Match score display, Messaging...", key="req_features")
            compliance_requirements = st.text_input("Regulatory or Compliance Constraints", placeholder="e.g. DPDP Act (India), GDPR, SSL, High-availability...", key="req_compliance")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_req_btn = st.button("✨ Execute Requirements Agent", key="btn_exec_req")
            
        if st.session_state.requirements_result:
            # 💬 Chat & Refine Section (ReAct Agent)
            st.markdown("---")
            st.markdown("### 💬 Chat & Refine PRD Requirements")
            
            chat_container = st.container(height=350)
            with chat_container:
                if "req_chat_history" not in st.session_state:
                    st.session_state.req_chat_history = []
                for msg in st.session_state.req_chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            
            chat_input = st.chat_input("Suggest changes, ask to rewrite, or Q&A about this document...", key="chat_input_req")
            if chat_input:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                st.session_state.req_chat_history.append({"role": "user", "content": chat_input})
                
                with st.chat_message("assistant"):
                    response = run_document_refiner(
                        chat_history=st.session_state.req_chat_history[:-1],
                        user_message=chat_input,
                        project_folder=st.session_state.get("current_project", "default_project"),
                        target_doc="prd_requirements.md",
                        agent_system_prompt=CHAT_SYSTEM_PROMPT,
                        selected_model=selected_model,
                        llm_engine=llm_engine,
                        server_host=server_host
                    )
                st.session_state.req_chat_history.append({"role": "assistant", "content": response})
                
                # Reload document from disk to ensure UI is in sync
                import os
                from utils import get_docs_dir
                doc_path = os.path.join(get_docs_dir(), "prd_requirements.md")
                if os.path.exists(doc_path):
                    with open(doc_path, "r", encoding="utf-8") as f:
                        st.session_state.requirements_result = f.read()
                        
                st.rerun()
        
    with col_out:
        if generate_req_btn:
            if not st.session_state.shared_idea.strip():
                st.warning("⚠️ Please describe your Business Idea in the field above first.")
            else:
                st.session_state.requirements_result = ""
                with st.container(border=True):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        '<div class="agent-thinking">'
                        'Synthesizing Product Requirements Document (PRD)'
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
                            target_roles=target_roles,
                            key_features=key_features,
                            compliance_requirements=compliance_requirements,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        
                        st.session_state.requirements_result = full_text
                        save_result(full_text)
                        st.toast("✅ Automatically saved 'prd_requirements.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.requirements_result:
            # 👁️ View / ✍️ Edit Mode Toggle
            edit_mode = st.toggle("✍️ Edit Document Manually", key="edit_mode_req")
            
            if edit_mode:
                edited_text = st.text_area(
                    "Edit Requirements Document", 
                    value=st.session_state.requirements_result, 
                    height=400, 
                    key="txt_edit_req"
                )
                if st.button("💾 Save Changes", key="save_req_manual", use_container_width=True):
                    save_result(edited_text)
                    st.session_state.requirements_result = edited_text
                    st.toast("✅ Manual edits saved successfully!")
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(st.session_state.requirements_result)
            
            col_dl, col_sav = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ Download as PRD Markdown",
                    data=st.session_state.requirements_result,
                    file_name="prd_requirements.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_req"
                )
            with col_sav:
                if st.button("💾 Save to Shared Memory", key="sav_req_btn", use_container_width=True):
                    save_result(st.session_state.requirements_result)
                    st.toast("✅ Saved 'prd_requirements.md' to Shared Memory!")
                    st.rerun()
                    
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">📑</div>
                <div class="title">Requirements Agent</div>
                <div class="sub">Click "Execute" on the left to synthesize the Product Requirements Document (PRD).</div>
            </div>
            """, unsafe_allow_html=True)
