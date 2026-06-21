import streamlit as st
import os
from agents.vision_mission_logic import (
    execute_agent_stream,
    save_result
)

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
