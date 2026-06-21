import streamlit as st
from agents.research_logic import (
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
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>vision_mission.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="handoff-status handoff-pending">
                    ⚠️ <strong>Handoff Pending:</strong> No <code>vision_mission.md</code> found. Execute the Vision & Mission agent first for best branding alignment.
                </div>
                """, unsafe_allow_html=True)
            
            competitors = st.text_input("Known Competitors / Alternatives", placeholder="e.g. Swiggy, Zomato, local tiffin services...", key="res_competitors")
            region = st.text_input("Target Location / Region", placeholder="e.g. Bangalore, Mumbai, Pan-India...", key="res_region")
            market_details = st.text_area("Specific Market Questions / Context", placeholder="e.g. Focus on corporate employee spending behaviors during work hours...", key="res_details")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_res_btn = st.button("✨ Execute Research Agent", key="btn_exec_res")
        
    with col_out:
        if generate_res_btn:
            if not st.session_state.shared_idea.strip():
                st.warning("⚠️ Please describe your Business Idea in the field above first.")
            else:
                st.session_state.research_result = ""
                with st.container(border=True):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        '<div class="agent-thinking">'
                        'Performing Market Research & Discovery'
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
                            competitors=competitors,
                            region=region,
                            market_details=market_details,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        
                        st.session_state.research_result = full_text
                        save_result(full_text)
                        st.toast("✅ Automatically saved 'market_research.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.research_result:
            with st.container(border=True):
                st.markdown(st.session_state.research_result)
            
            col_dl, col_sav = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ Download as Markdown",
                    data=st.session_state.research_result,
                    file_name="market_research.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_res"
                )
            with col_sav:
                if st.button("💾 Save to Shared Memory", key="sav_res_btn", use_container_width=True):
                    save_result(st.session_state.research_result)
                    st.toast("✅ Saved 'market_research.md' to Shared Memory!")
                    st.rerun()
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">🔍</div>
                <div class="title">Research &amp; Discovery Agent</div>
                <div class="sub">Click "Execute" on the left to analyze market potential.</div>
            </div>
            """, unsafe_allow_html=True)
