import streamlit as st
import os

# Import from local logic and common package
from logic import (
    check_handoff_status, execute_agent_stream, save_result,
    get_doc_for_lens, load_subagent, SUBAGENT_REGISTRY
)
from common import run_document_refiner, get_docs_dir, strip_yaml_front_matter

# ---------------------------------------------------------------
# Lens metadata for display
# ---------------------------------------------------------------
LENS_META = {
    "Summary":        {"icon": "🏗️", "label": "Summary",        "chat_title": "Architecture Summary"},
    "Business":       {"icon": "💼", "label": "Business",       "chat_title": "Business Architecture"},
    "Application":    {"icon": "📱", "label": "Application",    "chat_title": "Application Architecture"},
    "Security":       {"icon": "🔒", "label": "Security",       "chat_title": "Security Architecture"},
    "Infrastructure": {"icon": "☁️", "label": "Infrastructure", "chat_title": "Infrastructure Architecture"},
    "Data":           {"icon": "💾", "label": "Data",           "chat_title": "Data Architecture"},
}

LENS_ORDER = ["Summary", "Business", "Application", "Security", "Infrastructure", "Data"]


def render(selected_model, llm_engine, server_host):
    # ---------------------------------------------------------------
    # Lens Selector — tabs across the top
    # ---------------------------------------------------------------
    tab_labels = [f"{LENS_META[l]['icon']} {LENS_META[l]['label']}" for l in LENS_ORDER]
    tabs = st.tabs(tab_labels)

    for i, lens in enumerate(LENS_ORDER):
        with tabs[i]:
            _render_lens(lens, selected_model, llm_engine, server_host)


def _render_lens(lens: str, selected_model: str, llm_engine: str, server_host: str):
    """Renders the input + output panel for a single architecture lens."""

    target_doc = get_doc_for_lens(lens)
    meta = LENS_META[lens]

    # Load existing document content from disk
    proj_dir = get_docs_dir()
    filepath = os.path.join(proj_dir, target_doc)
    current_content = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                current_content = strip_yaml_front_matter(f.read())
        except Exception:
            pass

    col_input, col_out = st.columns([1, 1.2])

    # ------------------------------------------------------------------
    # LEFT COLUMN — controls
    # ------------------------------------------------------------------
    with col_input:
        with st.container(border=True):
            st.markdown(
                f'<div class="section-label">{meta["icon"]} {meta["label"]} Subagent</div>',
                unsafe_allow_html=True
            )

            # Handoff status badge
            status_class, status_text = check_handoff_status()
            st.markdown(
                f'<div class="handoff-status {status_class}">{status_text}</div>',
                unsafe_allow_html=True
            )

            tech_pref  = st.text_input("Tech Stack Preferences",
                                        placeholder="e.g. Python (FastAPI), React, Postgres...",
                                        key=f"tech_{lens}")
            scale      = st.text_input("Expected Traffic / User Base",
                                        placeholder="e.g. 100 orders/day, up to 10k users/month...",
                                        key=f"scale_{lens}")
            compliance = st.text_input("Compliance / Safety Needs",
                                        placeholder="e.g. Indian DPDP, PCI-DSS...",
                                        key=f"compliance_{lens}")

            st.markdown("<br>", unsafe_allow_html=True)
            execute_btn = st.button(
                f"✨ Execute {meta['label']} Subagent",
                key=f"btn_exec_{lens}",
                use_container_width=True
            )

        # Subagent skill viewer (expander)
        with st.expander(f"📋 View {meta['label']} Subagent Skills & Instructions"):
            try:
                sa = load_subagent(lens)
                st.markdown("**🎭 System Prompt**")
                st.markdown(sa["system_prompt"])
                st.markdown("---")
                st.markdown("**🛠️ Skills**")
                st.markdown(sa["skills"])
                st.markdown("---")
                st.markdown("**📋 Output Instructions**")
                st.markdown(sa["instructions"])
            except Exception as e:
                st.error(f"Could not load subagent files: {e}")

    # ------------------------------------------------------------------
    # Floating chat popover — rendered OUTSIDE columns at tab root level
    # so that position:fixed CSS applies to the full viewport
    # ------------------------------------------------------------------
    if current_content:
        _render_chat_popover(lens, target_doc, meta, selected_model, llm_engine, server_host)

    # ------------------------------------------------------------------
    # RIGHT COLUMN — output
    # ------------------------------------------------------------------
    with col_out:
        if execute_btn:
            if not st.session_state.get("shared_idea", "").strip():
                st.warning("⚠️ Please describe your Business Idea above first.")
            else:
                with st.container(border=True):
                    status_ph = st.empty()
                    status_ph.markdown(
                        f'<div class="agent-thinking">'
                        f'Designing {meta["label"]} Architecture'
                        f'<span class="thinking-dot"></span>'
                        f'<span class="thinking-dot"></span>'
                        f'<span class="thinking-dot"></span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    output_ph = st.empty()
                    full_text = ""
                    try:
                        stream = execute_agent_stream(
                            lens=lens,
                            shared_idea=st.session_state.shared_idea,
                            tech_pref=tech_pref,
                            scale=scale,
                            compliance=compliance,
                            selected_model=selected_model,
                            llm_engine=llm_engine,
                            server_host=server_host
                        )
                        for chunk in stream:
                            full_text += chunk
                            status_ph.empty()
                            output_ph.markdown(full_text)

                        save_result(lens, full_text, selected_model, llm_engine, server_host)
                        st.toast(f"✅ Saved '{target_doc}' to Shared Memory!")
                        st.rerun()
                    except Exception as e:
                        status_ph.error(f"Error: {e}")

        elif current_content:
            edit_mode = st.toggle("✍️ Edit Manually", key=f"edit_{lens}")

            if edit_mode:
                edited = st.text_area(
                    "Edit Document", value=current_content,
                    height=450, key=f"ta_edit_{lens}"
                )
                if st.button("💾 Save Changes", key=f"save_man_{lens}", use_container_width=True):
                    save_result(lens, edited, selected_model, llm_engine, server_host)
                    st.toast("✅ Manual edits saved!")
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(current_content)

            col_dl, col_sv = st.columns(2)
            with col_dl:
                st.download_button(
                    label="⬇️ Download Markdown",
                    data=current_content,
                    file_name=target_doc,
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"dl_{lens}"
                )
            with col_sv:
                if st.button("💾 Save to Shared Memory", key=f"sv_{lens}", use_container_width=True):
                    save_result(lens, current_content, selected_model, llm_engine, server_host)
                    st.toast(f"✅ Saved '{target_doc}'!")
                    st.rerun()
        else:
            st.markdown(f"""
            <div class="empty-agent-state">
                <div class="icon">{meta['icon']}</div>
                <div class="title">{meta['label']} Architecture</div>
                <div class="sub">Click "Execute {meta['label']} Subagent" on the left to generate this lens.</div>
            </div>
            """, unsafe_allow_html=True)


def _render_chat_popover(lens: str, target_doc: str, meta: dict,
                          selected_model: str, llm_engine: str, server_host: str):
    """Floating chat popover for refining the active lens document."""
    st.markdown("""
    <style>
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 30px !important;
        left: 30px !important;
        right: auto !important;
        top: auto !important;
        z-index: 999999 !important;
    }
    div[data-testid="stPopover"] button {
        border-radius: 50% !important;
        width: 65px !important;
        height: 65px !important;
        font-size: 30px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.2s ease-in-out !important;
    }
    div[data-testid="stPopover"] button:hover {
        transform: scale(1.1) !important;
    }
    div[data-testid="stPopover"] button svg { display: none !important; }
    div[data-testid="stPopoverBody"] {
        width: 420px !important;
        max-width: 90vw !important;
        border-radius: 16px !important;
        box-shadow: 0 12px 40px rgba(0,0,0,0.25) !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        background-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Load the system prompt for the chat agent from the subagent files
    try:
        sa = load_subagent(lens)
        chat_system_prompt = (
            f"You are the {meta['chat_title']} Chat Assistant.\n\n"
            f"{sa['system_prompt']}\n\n"
            f"{sa['skills']}\n\n"
            f"Your target document is '{target_doc}'. "
            f"Use tools to read and write updates when the user asks for changes."
        )
    except Exception:
        chat_system_prompt = (
            f"You are an architecture assistant. "
            f"Your target document is '{target_doc}'. Use tools to read and write updates."
        )

    chat_key = f"chat_hist_{lens}"

    with st.popover("💬"):
        st.markdown(
            f"<h3 style='margin-top:0;'>💬 Refine: {meta['chat_title']}</h3>",
            unsafe_allow_html=True
        )
        chat_container = st.container(height=350)
        with chat_container:
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []
            for msg in st.session_state[chat_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        chat_input = st.chat_input(
            "Ask a question or suggest a change...",
            key=f"chat_in_{lens}"
        )
        if chat_input:
            with st.chat_message("user"):
                st.markdown(chat_input)
            st.session_state[chat_key].append({"role": "user", "content": chat_input})

            with st.chat_message("assistant"):
                response = run_document_refiner(
                    chat_history=st.session_state[chat_key][:-1],
                    user_message=chat_input,
                    project_folder=st.session_state.get("current_project", "default_project"),
                    target_doc=target_doc,
                    agent_system_prompt=chat_system_prompt,
                    selected_model=selected_model,
                    llm_engine=llm_engine,
                    server_host=server_host
                )
            st.session_state[chat_key].append({"role": "assistant", "content": response})
            st.rerun()
