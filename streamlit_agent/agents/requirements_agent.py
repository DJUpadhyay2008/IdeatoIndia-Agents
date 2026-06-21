import streamlit as st
from agents.requirements_logic import (
    get_handoff_files_present,
    execute_agent_stream,
    save_result
)

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
