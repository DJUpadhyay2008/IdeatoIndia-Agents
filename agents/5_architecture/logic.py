import os
import sys

# Import from common package
from common import stream_chat, save_document, load_shared_memory, get_docs_dir

# ---------------------------------------------------------------
# Subagent Registry — maps lens name to folder and output doc
# ---------------------------------------------------------------
SUBAGENT_REGISTRY = {
    "Summary":        {"folder": "summary",        "doc": "architecture_summary.md"},
    "Application":    {"folder": "application",    "doc": "architecture_application.md"},
    "Business":       {"folder": "business",       "doc": "architecture_business.md"},
    "Security":       {"folder": "security",       "doc": "architecture_security.md"},
    "Infrastructure": {"folder": "infrastructure", "doc": "architecture_infrastructure.md"},
    "Data":           {"folder": "data",           "doc": "architecture_data.md"},
}

# Directory containing the subagent skill files
_HERE = os.path.dirname(os.path.abspath(__file__))
SUBAGENTS_DIR = os.path.join(_HERE, "subagents")

# Token budget (llama.cpp default context = 8192 tokens ≈ ~6 chars/token)
# Reserve ~2000 tokens for user prompt + response, leaving ~6192 for system.
# ~6192 tokens × 4 chars/token ≈ 24768 chars max for system — but we keep it
# tighter so shared memory + instructions also fit comfortably.
MAX_SYSTEM_CHARS  = 3200   # system_prompt + skills + instructions combined
MAX_MEMORY_CHARS  = 1000   # shared memory snippet injected into user prompt


def _read_file(path: str) -> str:
    """Safely read a file, returning empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def load_subagent(lens: str) -> dict:
    """
    Loads the externalized prompt files for a given lens.
    Returns a dict with keys: system_prompt, skills, instructions.
    """
    reg = SUBAGENT_REGISTRY.get(lens)
    if not reg:
        raise ValueError(f"Unknown lens: '{lens}'. Available: {list(SUBAGENT_REGISTRY.keys())}")

    folder = os.path.join(SUBAGENTS_DIR, reg["folder"])
    return {
        "system_prompt":  _read_file(os.path.join(folder, "system_prompt.md")),
        "skills":         _read_file(os.path.join(folder, "skills.md")),
        "instructions":   _read_file(os.path.join(folder, "instructions.md")),
        "doc":            reg["doc"],
        "lens":           lens,
    }


def build_full_system_prompt(subagent: dict) -> str:
    """
    Combines system_prompt + skills + instructions into one system message.
    Truncates intelligently to stay within llama.cpp context limits.
    Priority: instructions > system_prompt > skills (skills trimmed first).
    """
    sp   = subagent["system_prompt"]
    sk   = subagent["skills"]
    inst = subagent["instructions"]

    # Always include full system_prompt + instructions; trim skills if needed
    base = f"{sp}\n\n---\n{inst}"
    remaining = MAX_SYSTEM_CHARS - len(base) - 10  # 10 char separator buffer

    if remaining > 200 and sk:
        # Fit as much of skills as possible
        skills_snippet = sk[:remaining]
        if len(sk) > remaining:
            skills_snippet += "\n...(truncated)"
        full = f"{sp}\n\n---\n{skills_snippet}\n\n---\n{inst}"
    else:
        full = base

    return full


def get_doc_for_lens(lens: str) -> str:
    """Returns the target markdown filename for a given lens."""
    return SUBAGENT_REGISTRY.get(lens, {}).get("doc", "architecture_summary.md")


def check_handoff_status() -> tuple:
    """Returns (status_class, status_text) based on prior files existence."""
    if os.path.exists(os.path.join(get_docs_dir(), "prd_requirements.md")):
        return (
            "handoff-active",
            "🟢 <strong>Handoff Active:</strong> Successfully loaded prd_requirements.md from Shared Memory!"
        )
    return (
        "handoff-pending",
        "⚠️ <strong>Handoff Pending:</strong> No Requirements doc detected. Run Requirements agent first."
    )


def generate_user_prompt(lens: str, shared_idea: str, tech_pref: str = "",
                         scale: str = "", compliance: str = "") -> str:
    """Builds the user-turn prompt. Shared memory is capped to avoid token overflow."""
    memory_ctx = load_shared_memory()
    prompt = f"### Architecture Scope: {lens} Lens\n"
    prompt += f"**Business Idea:** {shared_idea}\n"
    if tech_pref:
        prompt += f"**Tech Preferences:** {tech_pref}\n"
    if scale:
        prompt += f"**Expected Scale:** {scale}\n"
    if compliance:
        prompt += f"**Compliance / Safety:** {compliance}\n"
    if memory_ctx:
        # Cap shared memory to avoid blowing token budget
        snippet = memory_ctx[:MAX_MEMORY_CHARS]
        if len(memory_ctx) > MAX_MEMORY_CHARS:
            snippet += "\n...(context truncated to fit token budget)"
        prompt += f"\n**Reference Context from Shared Memory:**\n{snippet}"
    return prompt


def execute_agent_stream(lens: str, shared_idea: str, tech_pref: str,
                         scale: str, compliance: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """
    Runs the streaming generation for the selected lens subagent.
    Loads system_prompt + skills + instructions from the subagents/ folder.
    """
    subagent = load_subagent(lens)
    system_prompt = build_full_system_prompt(subagent)
    user_prompt = generate_user_prompt(lens, shared_idea, tech_pref, scale, compliance)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    return stream_chat(messages, selected_model, llm_engine, server_host)


def save_result(lens: str, content: str):
    """Saves the generated content to the correct lens document."""
    doc_name = get_doc_for_lens(lens)
    save_document(doc_name, content)
