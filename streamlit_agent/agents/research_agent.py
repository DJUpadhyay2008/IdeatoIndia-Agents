import streamlit as st
from agents.research_logic import (
    check_handoff_status,
    execute_agent_stream,
    save_result
)
from agents.graph_agent import run_document_refiner

CHAT_SYSTEM_PROMPT = """You are the Market Research & Discovery Chat Assistant. Your job is to help the user understand, refine, and update the 'market_research.md' file.
You have access to tools to read the current document, write updates to the document, and inspect other files in the workspace.
If the user asks you to modify sections of the Market Landscape, Competitive Analysis, or Go-to-Market strategy, use your tools to update the document, and then explain the updates you made.
Be professional, structured, and helpful."""

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
            # 👁️ View / ✍️ Edit Mode Toggle
            edit_mode = st.toggle("✍️ Edit Document Manually", key="edit_mode_res")
            
            if edit_mode:
                edited_text = st.text_area(
                    "Edit Market Research Document", 
                    value=st.session_state.research_result, 
                    height=400, 
                    key="txt_edit_res"
                )
                if st.button("💾 Save Changes", key="save_res_manual", use_container_width=True):
                    save_result(edited_text)
                    st.session_state.research_result = edited_text
                    st.toast("✅ Manual edits saved successfully!")
                    st.rerun()
            else:
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
                    
            # 💬 Chat & Refine Section (ReAct Agent)
            st.markdown("---")
            st.markdown("### 💬 Chat & Refine Market Research")
            
            if "res_chat_history" not in st.session_state:
                st.session_state.res_chat_history = []
                
            for msg in st.session_state.res_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            chat_input = st.chat_input("Suggest changes, ask to rewrite, or Q&A about this document...", key="chat_input_res")
            if chat_input:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                st.session_state.res_chat_history.append({"role": "user", "content": chat_input})
                
                with st.chat_message("assistant"):
                    response = run_document_refiner(
                        chat_history=st.session_state.res_chat_history[:-1],
                        user_message=chat_input,
                        project_folder=st.session_state.get("current_project", "default_project"),
                        target_doc="market_research.md",
                        agent_system_prompt=CHAT_SYSTEM_PROMPT,
                        selected_model=selected_model,
                        llm_engine=llm_engine,
                        server_host=server_host
                    )
                st.session_state.res_chat_history.append({"role": "assistant", "content": response})
                st.rerun()
                
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">🔍</div>
                <div class="title">Research &amp; Discovery Agent</div>
                <div class="sub">Click "Execute" on the left to analyze market potential.</div>
            </div>
            """, unsafe_allow_html=True)
