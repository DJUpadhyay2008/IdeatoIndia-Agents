import streamlit as st
import os
from utils import stream_chat, save_document, load_shared_memory

SYSTEM_PROMPT = """You are an expert business strategist and brand consultant with 20+ years of experience helping startups and enterprises craft powerful brand identities.

When a business owner shares their idea, you will produce EXACTLY the following structured output — nothing more, nothing less:

---

## 🎯 Vision Statement
A single, inspiring, forward-looking sentence (15–25 words) describing the world this business aims to create. It should be aspirational, timeless, and emotionally resonant.

## 🚀 Mission Statement
A clear, action-oriented statement (2–4 sentences) explaining what the business does, who it serves, how it does it, and the value it delivers today.

## 💡 Core Values
List exactly 5 core values as short titles with a one-line explanation each.

## 🌟 Brand Promise
One punchy sentence (under 15 words) that captures what customers can always expect.

---

Be bold, specific, and avoid corporate clichés. Tailor everything to the specific idea, industry, and audience provided."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Info (V&M has no prerequisites, but shows it is the starting point)
            st.markdown("""
            <div style="background: rgba(217,119,6,0.1); border: 1px solid rgba(217,119,6,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #d97706;">
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
                        '<div style="text-align:center;padding:1rem;color:#ea580c;font-weight:700;">'
                        'Synthesizing Brand Identity'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '<span class="thinking-dot"></span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    output_placeholder = st.empty()
                    
                    # Context injections (Load shared memory context if any exist)
                    memory_ctx = load_shared_memory()
                    user_prompt = f"**Business Idea:** {st.session_state.shared_idea}\n"
                    if industry: user_prompt += f"**Industry:** {industry}\n"
                    if audience: user_prompt += f"**Target Audience:** {audience}\n"
                    if principles: user_prompt += f"**Core Values:** {principles}\n"
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
                        st.session_state.vision_mission_result = full_text
                        save_document("vision_mission.md", full_text)
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
                    save_document("vision_mission.md", st.session_state.vision_mission_result)
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
