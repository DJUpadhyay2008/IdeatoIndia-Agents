import streamlit as st
import os
from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

SYSTEM_PROMPT = """You are a Market Research Analyst and Competitive Intelligence Specialist. Your goal is to analyze the market landscape, target audience, and potential competitors for the business idea.

Using the provided business idea and optional context, you will produce EXACTLY the following structured output:

## 📊 Market Landscape & Trends
- **Market Size & Growth:** High-level estimate or qualitative assessment of the opportunity.
- **Key Industry Drivers:** E.g., digital adoption, regulatory shifts.
- **Target Audience Segmentation:** Clear profiles of the main customer groups.

## ⚔️ Competitive Analysis & Position
- **Direct Competitors:** List 2-3 specific competitors or current alternatives.
- **Competitor Strengths & Weaknesses:** What they do well, and where they fall short.
- **Our Unfair Advantage / USP:** How we can uniquely stand out in this market.

## 🚀 Recommended Go-to-Market (GTM)
- **Primary Channels:** Where to find and acquire customers.
- **Positioning Statement:** How to describe the offering to target customers.

Provide realistic, market-specific details. Focus on actionable insights rather than broad generalities."""

def render(selected_model, llm_engine, server_host):
    col_input, col_out = st.columns([1, 1.2])
    with col_input:
        with st.container(border=True):
            st.markdown('<div class="section-label">Agent Configurations</div>', unsafe_allow_html=True)
            
            # Handoff Detection
            has_vm = os.path.exists(os.path.join(get_docs_dir(), "vision_mission.md"))
            if has_vm:
                st.markdown("""
                <div style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #22c55e;">
                    🟢 <strong>Handoff Active:</strong> Successfully loaded <code>vision_mission.md</code> from Shared Memory!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; color: #eab308;">
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
                        '<div style="text-align:center;padding:1rem;color:#ea580c;font-weight:700;">'
                        'Performing Market Research & Discovery'
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
                    if competitors: user_prompt += f"**Competitors:** {competitors}\n"
                    if region: user_prompt += f"**Target Region:** {region}\n"
                    if market_details: user_prompt += f"**Market Context/Questions:** {market_details}\n"
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
                        st.session_state.research_result = full_text
                        save_document("market_research.md", full_text)
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
                    save_document("market_research.md", st.session_state.research_result)
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
