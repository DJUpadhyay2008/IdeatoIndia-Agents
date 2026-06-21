import streamlit as st
from agents.architecture_logic import (
    check_handoff_status,
    execute_agent_stream,
    save_result
)

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            if check_handoff_status():
                st.markdown("""
                <div class="handoff-status handoff-active">
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>prd_requirements.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="handoff-status handoff-pending">
                    ⚠️ <strong>Handoff Pending:</strong> No <code>prd_requirements.md</code> found. Run the Requirements Agent first to design matching database tables and API specs.
                </div>
                """, unsafe_allow_html=True)
            
            tech_pref = st.text_input("Tech Stack Preferences", placeholder="e.g. Python (FastAPI), React, Postgres, Supabase...", key="arch_tech")
            scale = st.text_input("Expected Traffic / User Base", placeholder="e.g. 100 orders/day at launch, up to 10k users/month in Year 1...", key="arch_scale")
            compliance = st.text_input("Compliance / Safety Needs", placeholder="e.g. Secure payment gateway integration, Indian DPDP compliance...", key="arch_compliance")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_arch_btn = st.button("✨ Execute Architecture Agent", key="btn_exec_arch")
        
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
