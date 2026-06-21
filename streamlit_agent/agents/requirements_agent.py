import streamlit as st
import os
from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

SYSTEM_PROMPT = """You are an expert Product Manager (PM) with 15+ years of experience defining product scope, writing Product Requirement Documents (PRDs), and creating user story backlogs.

Using the provided business idea and optional context, you will produce EXACTLY the following structured output:

## 📑 Product Requirements Document (PRD)

### 1. Product Overview & Core Objective
A clear summary of the product, its primary goal, and what problems it solves for the target users.

### 2. User Personas & Target Audience
List the key user roles (e.g., Job Seeker, Recruiter, Admin) and their primary goals.

### 3. Functional Requirements
A structured list of core modules and features required for the MVP:
- **Module A**: Description and features (e.g., Auth & Profiles).
- **Module B**: Description and features (e.g., Job Search & Apply).
- **Module C**: Description and features (e.g., matching engine).

### 4. Non-Functional Requirements (NFRs)
- **Performance**: Speed, load times, concurrency goals.
- **Scalability**: Target growth and user scaling.
- **Security & Privacy**: Data protection, auth compliance.
- **Usability**: Accessibility, device responsiveness.

### 5. User Stories & Acceptance Criteria
List 4-5 high-priority User Stories in the standard format:
- *As a [User], I want to [Action], so that [Benefit].*
  - **Acceptance Criteria**:
    - [ ] Criterion 1
    - [ ] Criterion 2

Be extremely detailed, structured, and realistic. Tailor the requirements to the specific business idea and constraints provided. Avoid placeholder text."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            has_vm = os.path.exists(os.path.join(get_docs_dir(), "vision_mission.md"))
            has_res = os.path.exists(os.path.join(get_docs_dir(), "market_research.md"))
            
            if has_vm and has_res:
                st.markdown("""
                <div style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #22c55e;">
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>vision_mission.md</code> and <code>market_research.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            elif has_vm or has_res:
                loaded_file = "vision_mission.md" if has_vm else "market_research.md"
                missing_file = "market_research.md" if has_vm else "vision_mission.md"
                st.markdown(f"""
                <div style="background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #eab308;">
                    ⚠️ <strong>Partial Handoff:</strong> Loaded <code>{loaded_file}</code>. Missing <code>{missing_file}</code>. We recommend running all previous agents first.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #eab308;">
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
                        '<div style="text-align:center;padding:1rem;color:#ea580c;font-weight:700;">'
                        'Synthesizing Product Requirements Document (PRD)'
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
                    if target_roles: user_prompt += f"**User Roles:** {target_roles}\n"
                    if key_features: user_prompt += f"**Core Features/Modules:** {key_features}\n"
                    if compliance_requirements: user_prompt += f"**Compliance/NFR Constraints:** {compliance_requirements}\n"
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
                        st.session_state.requirements_result = full_text
                        save_document("prd_requirements.md", full_text)
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
                    save_document("prd_requirements.md", st.session_state.requirements_result)
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
