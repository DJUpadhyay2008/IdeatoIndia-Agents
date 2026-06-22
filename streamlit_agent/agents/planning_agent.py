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
            status_class, status_text = check_handoff_status()
            st.markdown(f"""
            <div class="handoff-status {status_class}">
                {status_text}
            </div>
            """, unsafe_allow_html=True)
            
            timeline = st.selectbox("Launch Timeline Goal", ["3 Months", "6 Months", "1 Year"], index=1, key="plan_timeline")
            budget = st.text_input("Estimated Initial Capital", placeholder="e.g. 5 Lakhs INR, $10,000 bootstrap budget...", key="plan_budget")
            constraints = st.text_area("Operational/Team Constraints", placeholder="e.g. Solopreneur building first version, part-time help...", key="plan_constraints")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_plan_btn = st.button("✨ Execute Planning Agent", key="btn_exec_plan")
            
        if st.session_state.planning_result:
            # 💬 Floating Chat Refiner Popover (Ask Disha style, default bottom-left and draggable)
            st.markdown("""
            <style>
            /* Position the popover container as fixed on the bottom-left of screen */
            div[data-testid="stPopover"] {
                position: fixed !important;
                bottom: 30px !important;
                left: 30px !important;
                right: auto !important;
                top: auto !important;
                z-index: 999999 !important;
            }
            /* Style the button as a circular chat bubble */
            div[data-testid="stPopover"] button {
                border-radius: 50% !important;
                width: 65px !important;
                height: 65px !important;
                font-size: 30px !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
                background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%) !important;
                color: white !important;
                border: none !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: transform 0.2s ease-in-out !important;
                cursor: move !important;
            }
            div[data-testid="stPopover"] button:hover {
                transform: scale(1.1) !important;
                box-shadow: 0 10px 32px rgba(0,0,0,0.4) !important;
            }
            /* Hide the down arrow SVG icon inside the popover button */
            div[data-testid="stPopover"] button svg {
                display: none !important;
            }
            /* Adjust the floating popup window width/style */
            div[data-testid="stPopoverBody"] {
                width: 400px !important;
                max-width: 90vw !important;
                border-radius: 16px !important;
                box-shadow: 0 12px 40px rgba(0,0,0,0.25) !important;
                border: 1px solid rgba(0, 0, 0, 0.1) !important;
                background-color: #ffffff !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Inject Draggable Javascript Helper
            import streamlit.components.v1 as components
            components.html("""
            <script>
            function initDraggable() {
                const doc = window.parent.document;
                const el = doc.querySelector('div[data-testid="stPopover"]');
                if (!el) {
                    setTimeout(initDraggable, 100);
                    return;
                }
                
                // Set initial positioning styles if not already set
                if (!el.style.left || el.style.left === 'auto') {
                    el.style.setProperty('position', 'fixed', 'important');
                    el.style.setProperty('bottom', '30px', 'important');
                    el.style.setProperty('left', '30px', 'important');
                    el.style.setProperty('right', 'auto', 'important');
                    el.style.setProperty('top', 'auto', 'important');
                    el.style.setProperty('z-index', '999999', 'important');
                }
                
                const button = el.querySelector('button');
                if (!button) return;
                
                let isDragging = false;
                let startX, startY;
                let initialLeft, initialTop;
                
                button.addEventListener('mousedown', (e) => {
                    if (e.button !== 0) return; // left click only
                    isDragging = false;
                    startX = e.clientX;
                    startY = e.clientY;
                    
                    const rect = el.getBoundingClientRect();
                    initialLeft = rect.left;
                    initialTop = rect.top;
                    
                    function onMouseMove(moveEvent) {
                        const dx = moveEvent.clientX - startX;
                        const dy = moveEvent.clientY - startY;
                        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                            isDragging = true;
                        }
                        if (isDragging) {
                            el.style.setProperty('bottom', 'auto', 'important');
                            el.style.setProperty('right', 'auto', 'important');
                            el.style.setProperty('left', (initialLeft + dx) + 'px', 'important');
                            el.style.setProperty('top', (initialTop + dy) + 'px', 'important');
                        }
                    }
                    
                    function onMouseUp(upEvent) {
                        doc.removeEventListener('mousemove', onMouseMove);
                        doc.removeEventListener('mouseup', onMouseUp);
                    }
                    
                    doc.addEventListener('mousemove', onMouseMove);
                    doc.addEventListener('mouseup', onMouseUp);
                });
                
                button.addEventListener('click', (e) => {
                    if (isDragging) {
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }, true);
            }
            initDraggable();
            </script>
            """, height=0, width=0)
            
            with st.popover("💬"):
                st.markdown("<h3 style='margin-top:0;'>💬 Chat & Refine Launch Plan</h3>", unsafe_allow_html=True)
                
                chat_container = st.container(height=350)
                with chat_container:
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
                    
                    # Reload document from disk to ensure UI is in sync
                    import os
                    from utils import get_docs_dir
                    doc_path = os.path.join(get_docs_dir(), "launch_plan.md")
                    if os.path.exists(doc_path):
                        with open(doc_path, "r", encoding="utf-8") as f:
                            st.session_state.planning_result = f.read()
                            
                    st.rerun()
        
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
                    
        else:
            st.markdown("""
            <div class="empty-agent-state">
                <div class="icon">📋</div>
                <div class="title">Planning Agent</div>
                <div class="sub">Click "Execute" on the left to generate launch tasks and phases.</div>
            </div>
            """, unsafe_allow_html=True)
