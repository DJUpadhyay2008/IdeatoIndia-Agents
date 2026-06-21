import streamlit as st
import os
from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

SYSTEM_PROMPT = """You are a Principal Software Architect and Systems Engineer. Your goal is to design a robust, scalable, and cost-effective technical architecture for the business idea.

Using the provided business idea and optional context, you will produce EXACTLY the following structured output:

## 🛠️ Technology Stack Recommendations
- **Frontend:** Framework, hosting, state management.
- **Backend:** Language, framework, API design (REST/GraphQL).
- **Database:** Primary database (SQL vs NoSQL), caching layer, storage.
- **DevOps & Cloud:** Cloud provider, deployment platform, CI/CD pipeline.

## 💾 Database Schema & Data Models
Provide a clean representation of the core database tables/collections (at least 3-4 key models) with relationships:
- E.g., `Users Table`, `Products/Services Table`, `Orders/Transactions Table`.

## 🏗️ System Architecture Design
Describe the system architecture (e.g., client-server, microservices, serverless) and explain how data flows from user to database. Use simple diagrams or structured explanations to show component relationships.

## 🔒 Security, Compliance & Hosting
- **Security Best Practices:** Encryption (transit/rest), authentication/authorization (JWT/OAuth), protection.
- **Hosting & Infrastructure:** Recommendations for hosting on budget (e.g., Vercel, Supabase, AWS Free Tier).
- **Compliance:** Data privacy considerations (e.g., DPDP Act in India, GDPR).

Focus on cost-efficiency for the initial version while ensuring the path to scale is clear."""

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
                        '<div style="text-align:center;padding:1rem;color:#ea580c;font-weight:700;">'
                        'Designing Technical Architecture Specification'
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
                    if tech_pref: user_prompt += f"**Tech Preferences:** {tech_pref}\n"
                    if scale: user_prompt += f"**Expected Scale:** {scale}\n"
                    if compliance: user_prompt += f"**Compliance/Security:** {compliance}\n"
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
                        st.session_state.architecture_result = full_text
                        save_document("technical_architecture.md", full_text)
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
                    save_document("technical_architecture.md", st.session_state.architecture_result)
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
