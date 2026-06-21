import streamlit as st
import os
from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

SYSTEM_PROMPT = """You are a Startup Operations Specialist, Agile Coach, and Project Manager. Your goal is to break down the business idea and requirements into a practical launch roadmap and phase-by-phase task checklist.

Using the provided business idea and optional context, you will produce EXACTLY the following structured output:

## 📅 Startup Launch Roadmap & Phases

### Phase 1: MVP Setup & Foundations (Weeks 1-4)
- **Primary Goal:** What should be achieved in this phase.
- **Key Tasks:** Bulleted list of actionable development/business setup tasks.
- **Milestone:** The measurable outcome.

### Phase 2: Integration & Core Features (Weeks 5-8)
- **Primary Goal:** E.g., working matching logic, frontend integrations.
- **Key Tasks:** Bulleted list of actionable tasks.
- **Milestone:** The measurable outcome.

### Phase 3: Launch Prep & Alpha Testing (Weeks 9-12)
- **Primary Goal:** QA, deployment, user onboarding setup.
- **Key Tasks:** Bulleted list of tasks.
- **Milestone:** Beta release.

## 💰 Budget Outline & Resource Allocation
- **Estimated Setup Costs:** Domain, hosting, legal, initial marketing.
- **Operational Runway Needs:** Monthly estimated burn rate for software, team, marketing.
- **Resource Allocation:** Roles needed (e.g., Developer, Marketer, Operations) and their priorities.

Make the roadmap practical, high-impact, and tailored for lean execution."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            has_prd = os.path.exists(os.path.join(get_docs_dir(), "prd_requirements.md"))
            if has_prd:
                st.markdown("""
                <div style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #22c55e;">
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>prd_requirements.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #eab308;">
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
                        '<div style="text-align:center;padding:1rem;color:#ea580c;font-weight:700;">'
                        'Formulating Roadmap & Launch Checklist'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    output_placeholder = st.empty()
                    
                    # Context injections
                    memory_ctx = load_shared_memory()
                    user_prompt = f"**Business Idea:** {st.session_state.shared_idea}\n"
                    if timeline: user_prompt += f"**Timeline Goal:** {timeline}\n"
                    if budget: user_prompt += f"**Budget Details:** {budget}\n"
                    if constraints: user_prompt += f"**Operational Constraints:** {constraints}\n"
                    if memory_ctx:
                        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
                    
                    msgs = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ]
                    
                    full_text = ""
                    try:
                        for chunk in stream_chat(msgs, selected_model, llm_engine, server_host):
                            full_text += chunk
                            status_placeholder.empty()
                            output_placeholder.markdown(full_text)
                        st.session_state.planning_result = full_text
                        save_document("launch_plan.md", full_text)
                        st.toast("✅ Automatically saved 'launch_plan.md' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error: {e}")
                
        elif st.session_state.planning_result:
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
                    save_document("launch_plan.md", st.session_state.planning_result)
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
