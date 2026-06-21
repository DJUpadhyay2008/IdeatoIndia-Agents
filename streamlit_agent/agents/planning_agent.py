import streamlit as st
from agents.planning_logic import (
    check_handoff_status,
    execute_agent_stream,
    save_result
)
from agents.graph_agent import run_document_refiner

CHAT_SYSTEM_PROMPT = """You are the Operations & Project Planning Chat Assistant. Your job is to help the user understand, refine, and update the 'launch_plan.md' file.
You have access to tools to read the current document, write updates to the document, and inspect other files in the workspace.
If the user asks you to modify phases, milestones, timeline goals, tasks, budget outline, or resource allocation, use your tools to update the document, and then explain the updates you made.
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
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>prd_requirements.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="handoff-status handoff-pending">
                    ⚠️ <strong>Handoff Pending:</strong> No <code>prd_requirements.md</code> found. Run the Requirements Agent first to align launch roadmap with system specs.
                </div>
                """, unsafe_allow_html=True)
            
            timeline = st.selectbox("Launch Timeline Goal", ["3 Months", "6 Months", "1 Year"], index=1, key="plan_timeline")
            budget = st.text_input("Estimated Initial Capital", placeholder="e.g. 5 Lakhs INR, $10,000 bootstrap budget...", key="plan_budget")
            constraints = st.text_area("Operational/Team Constraints", placeholder="e.g. Solopreneur building first version, part-time help...", key="plan_constraints")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_plan_btn = st.button("✨ Execute Planning Agent", key="btn_exec_plan")
        
    with col_out:
        if generate_plan_btn:
            if not st.session_state.shared_idea.strip():
                st.warning("⚠️ Please describe your Business Idea in the field above first.")
            else:
                st.session_state.planning_result = ""
                with st.container(border=True):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        '<div class="agent-thinking">'
                        'Formulating Roadmap & Launch Checklist'
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
                            timeline=timeline,
                            budget=budget,
                            constraints=constraints,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        
                        st.session_state.planning_result = full_text
                        save_result(full_text)
                        st.toast("✅ Automatically saved 'launch_plan.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.planning_result:
            # 👁️ View / ✍️ Edit Mode Toggle
            edit_mode = st.toggle("✍️ Edit Document Manually", key="edit_mode_plan")
            
            if edit_mode:
                edited_text = st.text_area(
                    "Edit Launch Plan Document", 
                    value=st.session_state.planning_result, 
                    height=400, 
                    key="txt_edit_plan"
                )
                if st.button("💾 Save Changes", key="save_plan_manual", use_container_width=True):
                    save_result(edited_text)
                    st.session_state.planning_result = edited_text
                    st.toast("✅ Manual edits saved successfully!")
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(st.session_state.planning_result)
            
            col_dl, col_sav = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ Download as Markdown",
                    data=st.session_state.planning_result,
                    file_name="launch_plan.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_plan"
                )
            with col_sav:
                if st.button("💾 Save to Shared Memory", key="sav_plan_btn", use_container_width=True):
                    save_result(st.session_state.planning_result)
                    st.toast("✅ Saved 'launch_plan.md' to Shared Memory!")
                    st.rerun()
                    
            # 💬 Chat & Refine Section (ReAct Agent)
            st.markdown("---")
            st.markdown("### 💬 Chat & Refine Launch Plan")
            
            if "plan_chat_history" not in st.session_state:
                st.session_state.plan_chat_history = []
                
            for msg in st.session_state.plan_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            chat_input = st.chat_input("Suggest changes, ask to rewrite, or Q&A about this document...", key="chat_input_plan")
            if chat_input:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                st.session_state.plan_chat_history.append({"role": "user", "content": chat_input})
                
                with st.chat_message("assistant"):
                    response = run_document_refiner(
                        chat_history=st.session_state.plan_chat_history[:-1],
                        user_message=chat_input,
                        project_folder=st.session_state.get("current_project", "default_project"),
                        target_doc="launch_plan.md",
                        agent_system_prompt=CHAT_SYSTEM_PROMPT,
                        selected_model=selected_model,
                        llm_engine=llm_engine,
                        server_host=server_host
                    )
                st.session_state.plan_chat_history.append({"role": "assistant", "content": response})
                st.rerun()
                
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">📋</div>
                <div class="title">Planning Agent</div>
                <div class="sub">Click "Execute" on the left to generate launch tasks and phases.</div>
            </div>
            """, unsafe_allow_html=True)
