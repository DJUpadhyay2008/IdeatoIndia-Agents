import streamlit as st
import os
import requests
import json

from utils import (
    init_docs_dir,
    read_pdf,
    load_shared_memory,
    save_document,
    delete_document,
    get_ollama_models,
    stream_chat,
    get_docs_dir,
    list_projects,
    get_project_name_from_idea,
)

from agents import (
    vision_mission_agent,
    research_agent,
    requirements_agent,
    planning_agent,
    architecture_agent,
)

# Initialize shared documents directory
init_docs_dir()

# ---------------------------------------------------------------
# System Prompts for Chat Advisor
# ---------------------------------------------------------------
CHAT_SYSTEM_PROMPT = """You are a strategic startup assistant and advisor. You help the user build their business by discussing ideas, analyzing constraints, and answering questions about their documents.

You have access to the "Shared Memory" documents. When the user asks questions or requests assistance, analyze the documents in the shared memory and provide relevant, customized advice.

Always refer to the facts and plans described in the shared documents to ensure continuity."""

# ---------------------------------------------------------------
# Streamlit Page Setup
# ---------------------------------------------------------------
st.set_page_config(
    page_title="IdeaToIndia — Strategy Agent Harness",
    page_icon="🇮🇳",
    layout="wide",
)

# ---------------------------------------------------------------
# Session State Initialization (Theme / Accessibility options)
# ---------------------------------------------------------------
if "theme_preset" not in st.session_state:
    st.session_state.theme_preset = "Slate & Sky (Light)"
if "text_color_choice" not in st.session_state:
    st.session_state.text_color_choice = "Charcoal (#1e293b)"
if "font_size_choice" not in st.session_state:
    st.session_state.font_size_choice = "Normal"

# Resolve Theme variables for global style overrides
preset = st.session_state.theme_preset
txt_color_raw = st.session_state.text_color_choice
font_scale = st.session_state.font_size_choice

# Defaults
bg_app = "#f8fafc"
bg_app_image = "radial-gradient(circle at 50% 30%, #f0fdf4 0%, #e0f2fe 50%, #fffbeb 100%)"
bg_card = "#ffffff"
border_card = "#e2e8f0"
border_top_card = "#0ea5e9"
bg_sidebar = "#f8fafc"
border_sidebar = "#e2e8f0"
text_sidebar = "#1e293b"

# Accessibility helper variables
color_output_header = "#065f46" # Emerald green default
bg_code = "#f1f5f9"
color_code = "#0f172a"
color_thinking = "#ea580c" # Brand orange default

# Default light theme values for handoff alerts
bg_handoff_ready = "#fffbeb"
border_handoff_ready = "#fde68a"
color_handoff_ready = "#92400e"

bg_handoff_active = "#f0fdf4"
border_handoff_active = "#bbf7d0"
color_handoff_active = "#166534"

# Adjust presets
if preset == "Pure High Contrast (Light)":
    bg_app = "#ffffff"
    bg_app_image = "none"
    bg_card = "#ffffff"
    border_card = "#000000"
    border_top_card = "#000000"
    bg_sidebar = "#ffffff"
    border_sidebar = "#000000"
    text_sidebar = "#000000"
    color_output_header = "#000000"
    bg_code = "#f1f5f9"
    color_code = "#000000"
    color_thinking = "#000000"
    
    bg_handoff_ready = "#ffffff"
    border_handoff_ready = "#000000"
    color_handoff_ready = "#000000"
    bg_handoff_active = "#ffffff"
    border_handoff_active = "#000000"
    color_handoff_active = "#000000"
elif preset == "Midnight Dark (Dark)":
    bg_app = "#0f172a"
    bg_app_image = "radial-gradient(circle at 50% 30%, #1e293b 0%, #0f172a 100%)"
    bg_card = "#1e293b"
    border_card = "#334155"
    border_top_card = "#38bdf8"
    bg_sidebar = "#0f172a"
    border_sidebar = "#334155"
    text_sidebar = "#f8fafc"
    color_output_header = "#34d399" # Bright Mint for dark mode
    bg_code = "#0f172a"
    color_code = "#38bdf8"
    color_thinking = "#fb923c" # bright orange
    
    bg_handoff_ready = "rgba(245, 158, 11, 0.15)"
    border_handoff_ready = "rgba(245, 158, 11, 0.35)"
    color_handoff_ready = "#fbbf24"
    bg_handoff_active = "rgba(16, 185, 129, 0.15)"
    border_handoff_active = "rgba(16, 185, 129, 0.35)"
    color_handoff_active = "#34d399"
elif preset == "Emerald Mint (Light)":
    bg_app = "#f0fdf4"
    bg_app_image = "radial-gradient(circle at 50% 30%, #ecfdf5 0%, #d1fae5 100%)"
    bg_card = "#ffffff"
    border_card = "#a7f3d0"
    border_top_card = "#10b981"
    bg_sidebar = "#f0fdf4"
    border_sidebar = "#a7f3d0"
    text_sidebar = "#065f46"
    color_output_header = "#047857"
    bg_code = "#ecfdf5"
    color_code = "#065f46"
    color_thinking = "#047857"
    
    bg_handoff_ready = "#fffbeb"
    border_handoff_ready = "#fde68a"
    color_handoff_ready = "#92400e"
    bg_handoff_active = "#f0fdf4"
    border_handoff_active = "#a7f3d0"
    color_handoff_active = "#047857"

# Resolve text color selection
if "Charcoal" in txt_color_raw:
    color_text = "#1e293b"
elif "Pure Black" in txt_color_raw:
    color_text = "#000000"
elif "Navy" in txt_color_raw:
    color_text = "#0f172a"
elif "Off-White" in txt_color_raw:
    color_text = "#f8fafc"
else:
    color_text = "#1e293b"

# Resolve font scale
if font_scale == "Normal":
    font_size_base = "0.95rem"
    font_size_small = "0.85rem"
    font_size_h1 = "2.2rem"
elif font_scale == "Medium-Large":
    font_size_base = "1.1rem"
    font_size_small = "0.95rem"
    font_size_h1 = "2.6rem"
else: # Extra Large
    font_size_base = "1.3rem"
    font_size_small = "1.1rem"
    font_size_h1 = "3rem"

# Inject the dynamic stylesheet
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');

/* ── Reset & base (with high-compatibility system font fallback) ── */
html, body, p, span, label, input, textarea, select, button, div, li, a {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
}}

html, body {{
    color: {color_text} !important;
}}

/* ── Full page background ── */
.stApp {{
    background-color: {bg_app} !important;
    background-image: {bg_app_image} !important;
    background-size: 100% 100%, 24px 24px;
    background-attachment: fixed;
    min-height: 100vh;
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}

/* ── Sidebar Control Panel ── */
[data-testid="stSidebar"] {{
    background-color: {bg_sidebar} !important;
    border-right: 1px solid {border_sidebar} !important;
    box-shadow: inset -3px 0 10px rgba(0,0,0,0.01) !important;
}}

/* Style all standard texts and labels inside sidebar to ensure high contrast & 100% opacity in all browsers */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p {{
    color: {text_sidebar} !important;
    opacity: 1 !important;
    font-weight: 500 !important;
}}

/* Darker header styling inside sidebar */
[data-testid="stSidebar"] .section-label {{
    color: #0369a1 !important; /* Sky 700 */
    font-size: 0.85rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.08em !important;
    margin-top: 1rem !important;
    margin-bottom: 0.75rem !important;
    display: block !important;
}}

/* Sidebar code block readability styling */
[data-testid="stSidebar"] code,
[data-testid="stSidebar"] pre {{
    color: #0f172a !important; /* slate-900 */
    background-color: #e2e8f0 !important; /* slate-200 */
    border: 1px solid #cbd5e1 !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}}

/* ── Input boxes (Clean white with sky-blue focus) ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select, select, div[role="listbox"], .stMultiSelect {{
    color: #0f172a !important; /* slate-900 */
    background-color: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 10px !important;
    box-shadow: 
        inset 1px 1px 3px rgba(0,0,0,0.05),
        0px 1px 0px rgba(255,255,255,0.8) !important;
    padding: 0.6rem 0.8rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {{
    border-color: #0ea5e9 !important;
    box-shadow: 
        inset 0px 1px 2px rgba(0,0,0,0.05),
        0 0 10px rgba(14, 165, 233, 0.25) !important;
    outline: none !important;
}}

/* Form labels - style them globally with high contrast dark slate color */
.stTextInput label, .stTextArea label, .stSelectbox label, .stMultiSelect label, label, [data-testid="stWidgetLabel"] p {{
    color: {color_text} !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.03em;
    margin-bottom: 0.4rem !important;
    opacity: 1 !important;
}}

/* ── Global placeholder coloring ── */
::placeholder {{
    color: #64748b !important; /* slate-500 */
    opacity: 1 !important;
}}
input::placeholder, textarea::placeholder {{
    color: #64748b !important;
    opacity: 1 !important;
}}

/* Fix upload text and drag-and-drop box */
[data-testid="stFileUploader"] {{
    background-color: #ffffff !important;
    border: 1.5px dashed #0ea5e9 !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
}}
[data-testid="stFileUploader"] * {{
    color: #334155 !important; /* slate-700 */
}}

/* ── Hero plaque ── */
.hero {{
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}}
.hero-badge {{
    display: inline-block;
    background: linear-gradient(135deg, #0ea5e9 0%, #10b981 100%) !important;
    color: #ffffff !important;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 0.4rem 1.2rem;
    border-radius: 6px;
    margin-bottom: 1.2rem;
    box-shadow: 0px 4px 10px rgba(14, 165, 233, 0.2) !important;
}}
.hero-badge * {{
    color: #ffffff !important;
}}
.hero-title {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    color: #0c4a6e !important; /* Sky 900 */
    line-height: 1.15;
    margin-bottom: 0.75rem;
}}
.hero-sub {{
    color: #334155 !important; /* slate-700 */
    font-size: 1.1rem;
    max-width: 580px;
    margin: 0 auto 2rem;
    line-height: 1.6;
}}

/* ── Tactile Raised Cards ── */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {bg_card} !important;
    background: {bg_card} !important;
    border: 1px solid {border_card} !important;
    border-top: 2px solid {border_top_card} !important;
    border-radius: 16px !important;
    box-shadow: 
        0 10px 15px -3px rgba(0,0,0,0.05),
        0 4px 6px -2px rgba(0,0,0,0.02) !important;
    padding: 1.75rem !important;
    margin-bottom: 1.5rem !important;
}}

/* Reset the inner wrapper to prevent double borders & double padding */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] [class*="e1f1d6gn1"] {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}}

/* Set text sizes based on scale choice (excluding inputs and layout wrappers) */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] p,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] li,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] span {{
    font-size: {font_size_base} !important;
}}

/* ── Clean Bright Output Sheet ── */
.stAppViewMain div[data-testid="column"]:nth-of-type(2) div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {bg_card} !important;
    background: {bg_card} !important;
    border: 2px solid #059669 !important; /* emerald-600 */
    border-top: 4px solid #059669 !important;
    border-radius: 16px !important;
    box-shadow: 
        0 20px 25px -5px rgba(16, 185, 129, 0.08),
        0 10px 10px -5px rgba(16, 185, 129, 0.04) !important;
    padding: 2.2rem !important;
}}

/* Ensure the output inner wrapper doesn't get the emerald border */
.stAppViewMain div[data-testid="column"]:nth-of-type(2) div[data-testid="stVerticalBlockBorderWrapper"] [class*="e1f1d6gn1"] {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}}

/* Re-color text elements on output card explicitly to solve Firefox theme clash (avoiding input fields/buttons) */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] p,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] span,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] li,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] strong,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] em,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] blockquote,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] td,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] th,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] a,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] ul,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] ol {{
    color: {color_text} !important;
}}

.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h1,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h2,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h3,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h4,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h5,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] h6,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] strong {{
    color: {color_output_header} !important;
    font-family: 'Playfair Display', serif !important;
}}

/* Code block customization inside containers */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] code {{
    background-color: {bg_code} !important;
    color: {color_code} !important;
    padding: 0.2rem 0.4rem !important;
    border-radius: 4px !important;
    font-family: monospace !important;
}}
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] pre {{
    background-color: {bg_code} !important;
    border: 1px solid {border_card} !important;
    padding: 1rem !important;
    border-radius: 8px !important;
}}
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] pre code {{
    background-color: transparent !important;
    padding: 0 !important;
}}

.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] hr {{
    border-color: rgba(16, 185, 129, 0.15) !important;
}}

/* ── Section Label ── */
.section-label {{
    font-size: 0.85rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #0369a1 !important; /* Sky 700 */
    margin-bottom: 0.75rem;
    display: block;
}}

/* ── Bright Gradient Push Button ── */
.stButton > button {{
    width: 100%;
    background: linear-gradient(135deg, #0ea5e9 0%, #10b981 100%) !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.75rem 2rem !important;
    font-size: 0.95rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    cursor: pointer !important;
    box-shadow: 
        0px 4px 10px rgba(14, 165, 233, 0.3),
        inset 0px 1px 0px rgba(255,255,255,0.4) !important;
    transition: all 0.2s ease !important;
}}
.stButton > button,
.stButton > button * {{
    color: #ffffff !important;
}}
.stButton > button:hover {{
    background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%) !important;
    box-shadow: 
        0px 6px 14px rgba(14, 165, 233, 0.4),
        inset 0px 1px 0px rgba(255,255,255,0.4) !important;
    transform: translateY(-1px);
}}
.stButton > button:active {{
    box-shadow: 
        0px 2px 4px rgba(14, 165, 233, 0.2),
        inset 0px 2px 4px rgba(0,0,0,0.1) !important;
    transform: translateY(1px) !important;
}}

/* ── Physical Folder Tabs (Sky Blue Theme - Firefox & Chrome compatible) ── */
div[data-testid="stTabs"] {{
    background-color: #f1f5f9 !important; /* slate-100 */
    border-radius: 12px 12px 0 0 !important;
    padding: 0.5rem 0.5rem 0 0.5rem !important;
    border: 1px solid #cbd5e1 !important;
    border-bottom: none !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
    gap: 4px !important;
}}
button[role="tab"] {{
    -moz-appearance: none !important;
    -webkit-appearance: none !important;
    background: #e2e8f0 !important; /* slate-200 */
    border: 1px solid #cbd5e1 !important;
    border-bottom: none !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.2s ease !important;
    margin-bottom: -1px !important;
}}
button[role="tab"] p,
button[role="tab"] span,
button[role="tab"] div,
button[role="tab"] {{
    color: #475569 !important; /* slate-600 */
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}}
button[role="tab"]:hover p,
button[role="tab"]:hover span,
button[role="tab"]:hover div,
button[role="tab"]:hover {{
    background: #e2e8f0 !important;
    color: #0f172a !important; /* slate-900 */
}}
button[role="tab"][aria-selected="true"] {{
    background: #ffffff !important;
    border-top: 3px solid #0369a1 !important; /* Sky 700 */
    border-bottom: 2px solid #ffffff !important;
    box-shadow: 0px -4px 12px rgba(14, 165, 233, 0.1) !important;
}}
button[role="tab"][aria-selected="true"] p,
button[role="tab"][aria-selected="true"] span,
button[role="tab"][aria-selected="true"] div,
button[role="tab"][aria-selected="true"] {{
    color: #0369a1 !important; /* Sky 700 */
    font-weight: 800 !important;
}}

/* Remove default focus ring in Firefox */
button::-moz-focus-inner {{
    border: 0 !important;
}}

/* ── Chat Advisor bubbles ── */
.chat-bubble {{
    padding: 1.1rem 1.6rem;
    border-radius: 16px;
    margin-bottom: 1.2rem;
    max-width: 80%;
    line-height: 1.65;
}}
.chat-bubble.user {{
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
    border: 1px solid #0284c7 !important;
    box-shadow: 
        0 4px 10px rgba(14, 165, 233, 0.2),
        inset 0 1px 0 rgba(255,255,255,0.3) !important;
    margin-left: auto;
    border-bottom-right-radius: 4px !important;
}}
.chat-bubble.user,
.chat-bubble.user * {{
    color: #ffffff !important;
}}
.chat-bubble.bot {{
    background: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    border-left: 4px solid #059669 !important; /* emerald-600 */
    box-shadow: 
        0px 4px 12px rgba(0,0,0,0.03),
        inset 1px 1px 0px rgba(255,255,255,1) !important;
    margin-right: auto;
    border-bottom-left-radius: 4px !important;
}}
.chat-bubble.bot,
.chat-bubble.bot * {{
    color: #1e293b !important;
}}

/* ── Thinking dots micro-animation ── */
.thinking-dot {{
    display: inline-block;
    width: 7px;
    height: 7px;
    background-color: #0ea5e9;
    border-radius: 50%;
    margin-left: 4px;
    animation: pulse 1.2s ease-in-out infinite;
}}
.thinking-dot:nth-child(2) {{ animation-delay: 0.2s; }}
.thinking-dot:nth-child(3) {{ animation-delay: 0.4s; }}

@keyframes pulse {{
    0%, 100% {{ transform: scale(1); opacity: 0.4; }}
    50% {{ transform: scale(1.4); opacity: 1; }}
}}

/* ── Fancy divider ── */
.fancy-divider {{
    height: 2px;
    background: linear-gradient(90deg, transparent, #0ea5e9 50%, transparent);
    margin: 2rem 0;
    opacity: 0.4;
}}

/* ── Expander Panel ── */
[data-testid="stExpander"] {{
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-top: 2px solid #059669 !important; /* emerald-600 */
    border-radius: 12px !important;
    box-shadow: 
        0px 4px 6px rgba(0,0,0,0.02),
        inset 1px 1px 0px rgba(255,255,255,1) !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 700 !important;
    color: #047857 !important;
}}

/* ── Empty Agent State Placeholder ── */
.empty-agent-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
    border: 2px dashed #cbd5e1 !important;
    border-radius: 16px;
    text-align: center;
    padding: 1.5rem;
    background: #f8fafc;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
}}
.empty-agent-state .icon {{
    font-size: 3rem;
    margin-bottom: 1rem;
    filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
}}
.empty-agent-state .title {{
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: #0f172a;
}}
.empty-agent-state .sub {{
    font-size: 0.85rem;
    line-height: 1.5;
    color: #475569;
}}

/* ── Handoff Status Alerts ── */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-status {{
    border-radius: 8px !important;
    padding: 0.75rem !important;
    margin-bottom: 1rem !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}}
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-ready,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-ready * {{
    background-color: {bg_handoff_ready} !important;
    border: 1px solid {border_handoff_ready} !important;
    color: {color_handoff_ready} !important;
}}
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-active,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-active * {{
    background-color: {bg_handoff_active} !important;
    border: 1px solid {border_handoff_active} !important;
    color: {color_handoff_active} !important;
}}
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-pending,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .handoff-pending * {{
    background-color: {bg_handoff_ready} !important;
    border: 1px solid {border_handoff_ready} !important;
    color: {color_handoff_ready} !important;
}}

/* ── Agent Thinking/Loading Indicator ── */
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .agent-thinking,
.stAppViewMain div[data-testid="stVerticalBlockBorderWrapper"] .agent-thinking * {{
    text-align: center !important;
    padding: 1rem !important;
    color: {color_thinking} !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
}}

/* ── Chat helper text ── */
.chat-helper-text {{
    color: #475569 !important;
    font-size: 0.9rem !important;
    margin-bottom: 0.5rem !important;
    line-height: 1.5 !important;
}}

/* ── Sidebar File Manager List (Compact & Perfectly Aligned) ── */
[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    margin-bottom: 0.25rem !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] details {{
    border: none !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    padding: 0.4rem 0.6rem !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #334155 !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stVerticalBlock"] {{
    padding: 0.5rem !important;
    font-size: 0.78rem !important;
    background: #f8fafc !important;
    border-top: 1px solid #cbd5e1 !important;
}}
/* Ensure filenames wrap nicely inside sidebar columns without overflow */
[data-testid="stSidebar"] [data-testid="column"] {{
    align-self: center !important;
}}
[data-testid="stSidebar"] [data-testid="column"]:nth-of-type(1) {{
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
/* Custom aligned delete buttons in sidebar */
[data-testid="stSidebar"] [data-testid="column"]:nth-of-type(2) .stButton > button {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    background: #fee2e2 !important;
    border: 1px solid #fca5a5 !important;
    color: #ef4444 !important;
    font-size: 0.95rem !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    margin: 0 !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stSidebar"] [data-testid="column"]:nth-of-type(2) .stButton > button:hover {{
    background: #fecaca !important;
    border-color: #f87171 !important;
    color: #dc2626 !important;
    transform: none !important;
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------
if "current_project" not in st.session_state:
    st.session_state.current_project = "default_project"

def load_project_state():
    proj_dir = get_docs_dir()
    file_map = {
        "vision_mission.md": "vision_mission_result",
        "market_research.md": "research_result",
        "prd_requirements.md": "requirements_result",
        "launch_plan.md": "planning_result",
        "technical_architecture.md": "architecture_result",
        "business_idea.txt": "shared_idea"
    }
    for var in file_map.values():
        st.session_state[var] = ""
    for filename, varname in file_map.items():
        filepath = os.path.join(proj_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    st.session_state[varname] = f.read()
            except Exception:
                pass

if "vision_mission_result" not in st.session_state:
    load_project_state()

if "vision_mission_result" not in st.session_state:
    st.session_state.vision_mission_result = ""
if "research_result" not in st.session_state:
    st.session_state.research_result = ""
if "requirements_result" not in st.session_state:
    st.session_state.requirements_result = ""
if "planning_result" not in st.session_state:
    st.session_state.planning_result = ""
if "architecture_result" not in st.session_state:
    st.session_state.architecture_result = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "shared_idea" not in st.session_state:
    st.session_state.shared_idea = ""

# ---------------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-badge">🇮🇳 IdeaToIndia · AI Startup Harness</div>
    <div class="hero-title">Core Strategy Workshop</div>
    <div class="hero-sub">
        Define your vision, research the market, outline launch roadmap, and architecture specs using a shared context memory.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Sidebar: Project Workspace, Settings & Shared Memory
# ---------------------------------------------------------------
st.sidebar.markdown('<div class="section-label">📁 Project Workspace</div>', unsafe_allow_html=True)

# List projects dynamically
projects = list_projects()
try:
    proj_index = projects.index(st.session_state.current_project)
except ValueError:
    proj_index = 0

selected_proj = st.sidebar.selectbox("Active Project Folder", projects, index=proj_index)
if selected_proj != st.session_state.current_project:
    st.session_state.current_project = selected_proj
    load_project_state()
    st.rerun()

with st.sidebar.expander("🆕 Create New Project"):
    new_proj_name = st.text_input("New Project Name", placeholder="e.g. HealthTech Startup", key="txt_new_project")
    if st.button("Create Project", use_container_width=True, key="btn_create_project"):
        if new_proj_name.strip():
            clean_name = "".join(c for c in new_proj_name if c.isalnum() or c in ['_', '-', ' ']).strip()
            if clean_name:
                st.session_state.current_project = clean_name
                get_docs_dir()
                load_project_state()
                st.toast(f"📁 Created & switched to project: {clean_name}")
                st.rerun()

st.sidebar.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="section-label">⚙️ Workspace Settings</div>', unsafe_allow_html=True)

# Engine & Model selection (Defaults to llama-server on GPU)
llm_engine = st.sidebar.selectbox("LLM Engine", ["Ollama", "llama.cpp (llama-server)", "Google Gemini API"], index=1)

if llm_engine == "Ollama":
    available_models = get_ollama_models()
    selected_model = st.sidebar.selectbox("Active AI Model", available_models, index=0)
    server_host = st.sidebar.text_input("Ollama Host URL", value="http://localhost:11434")
elif llm_engine == "Google Gemini API":
    gemini_api_key = st.sidebar.text_input("Google Gemini API Key", type="password", value=st.session_state.get("gemini_api_key", ""))
    st.session_state.gemini_api_key = gemini_api_key
    selected_model = st.sidebar.selectbox(
        "Active AI Model", 
        ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
        index=0
    )
    server_host = ""
else:
    selected_model = "gemma4"  # llama-server uses pre-loaded model
    server_host = st.sidebar.text_input("llama.cpp Host URL", value="http://localhost:8080")
    st.sidebar.markdown("""
    💡 **Run llama-server on GPU:**
    ```bash
    ../llama.cpp/build/bin/llama-server \\
      -hf unsloth/gemma-4-E2B-it-GGUF:UD-Q4_K_XL \\
      -ngl 999 -c 8192 -np 1 -t 8 --port 8080
    ```
    """)

# Theme & Accessibility Configuration Expander
with st.sidebar.expander("🎨 Theme & Accessibility"):
    theme_preset_choices = ["Slate & Sky (Light)", "Pure High Contrast (Light)", "Midnight Dark (Dark)", "Emerald Mint (Light)"]
    theme_preset = st.selectbox(
        "Theme Preset",
        theme_preset_choices,
        index=theme_preset_choices.index(st.session_state.theme_preset)
    )
    
    text_color_choices = ["Charcoal (#1e293b)", "Pure Black (#000000)", "Navy Blue (#0f172a)", "Bright Off-White (#f8fafc)"]
    text_color_choice = st.selectbox(
        "Text Color Focus",
        text_color_choices,
        index=text_color_choices.index(st.session_state.text_color_choice)
    )
    
    font_size_choices = ["Normal", "Medium-Large", "Extra Large"]
    font_size_choice = st.selectbox(
        "Font Size Scale",
        font_size_choices,
        index=font_size_choices.index(st.session_state.font_size_choice)
    )
    
    if (theme_preset != st.session_state.theme_preset or
        text_color_choice != st.session_state.text_color_choice or
        font_size_choice != st.session_state.font_size_choice):
        st.session_state.theme_preset = theme_preset
        st.session_state.text_color_choice = text_color_choice
        st.session_state.font_size_choice = font_size_choice
        st.rerun()

st.sidebar.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="section-label">📁 Shared Memory (Documents)</div>', unsafe_allow_html=True)

# Uploading new files
uploaded_file = st.sidebar.file_uploader("Upload to memory (.txt, .md, .pdf, .json)", type=["txt", "md", "pdf", "json"])
if uploaded_file is not None:
    try:
        content_bytes = uploaded_file.read()
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext == '.pdf':
            # Write temp file to parse it
            temp_path = os.path.join(get_docs_dir(), f"temp_{uploaded_file.name}")
            with open(temp_path, "wb") as f:
                f.write(content_bytes)
            pdf_text = read_pdf(temp_path)
            os.remove(temp_path)
            save_document(uploaded_file.name, pdf_text)
        else:
            text_content = content_bytes.decode("utf-8", errors="ignore")
            save_document(uploaded_file.name, text_content)
        
        st.sidebar.success(f"Uploaded: {uploaded_file.name}")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Failed to save file: {e}")

# Quick Note widget
with st.sidebar.expander("📝 Add Quick Note / Constraint"):
    note_name = st.text_input("Filename", value="constraints.txt")
    note_content = st.text_area("Note details", placeholder="e.g., Budget is strictly $500, launch in 2 months, mobile-first...")
    if st.button("Save Note", use_container_width=True):
        if note_name and note_content:
            if not note_name.endswith(('.txt', '.md', '.json')):
                note_name += ".txt"
            save_document(note_name, note_content)
            st.toast(f"✅ Note saved: {note_name}")
            st.rerun()

# Document manager listing files
files = os.listdir(get_docs_dir())
if not files:
    st.sidebar.info("Shared memory is currently empty. Upload files or generate agent documents below to build context!")
else:
    st.sidebar.markdown(f"**Files in Memory ({len(files)}):**")
    for file in sorted(files):
        col_name, col_del = st.sidebar.columns([0.8, 0.2])
        with col_name:
            with st.expander(f"📄 {file}", expanded=False):
                path = os.path.join(get_docs_dir(), file)
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.txt', '.md', '.json']:
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            st.text(f.read()[:600] + ("..." if len(f.read()) > 600 else ""))
                    except Exception as e:
                        st.error(f"Error: {e}")
                elif ext == '.pdf':
                    pdf_text = read_pdf(path)
                    st.text(pdf_text[:600] + ("..." if len(pdf_text) > 600 else ""))
                else:
                    st.text("Preview unavailable for this format.")
        with col_del:
            if st.button("🗑️", key=f"del_{file}", help=f"Remove {file} from memory"):
                delete_document(file)
                st.toast(f"🗑️ Removed {file}")
                st.rerun()

# ---------------------------------------------------------------
# Core Business Idea (Shared across all tabs)
# ---------------------------------------------------------------
with st.container(border=True):
    st.markdown('<div class="section-label">💡 Shared Business Idea</div>', unsafe_allow_html=True)
    shared_idea = st.text_area(
        "Describe your core business idea (this is automatically shared with all agents and chatbot below)",
        value=st.session_state.shared_idea,
        placeholder="e.g. A localized food delivery platform in India that connects home-cooked meal creators (home chefs) directly with corporate professionals seeking healthy lunches.",
        height=80,
    )
    if shared_idea != st.session_state.shared_idea:
        st.session_state.shared_idea = shared_idea
        
        # 1. Determine project name from the new idea
        new_proj = get_project_name_from_idea(shared_idea)
        
        # 2. If it is different from the current project, switch to it
        if new_proj != st.session_state.current_project:
            st.session_state.current_project = new_proj
            # Ensure folder is created
            proj_dir = get_docs_dir()
            # Save the business idea text to the new project's folder
            idea_path = os.path.join(proj_dir, "business_idea.txt")
            with open(idea_path, "w", encoding="utf-8") as f:
                f.write(shared_idea)
            # Load project state (this will load other files or clear them if empty)
            load_project_state()
            # Restore the new idea text back to session state so it doesn't get cleared by load_project_state
            st.session_state.shared_idea = shared_idea
            st.toast(f"📁 Switched to project: {new_proj}")
            st.rerun()
        else:
            # Same project, just update the business idea file
            proj_dir = get_docs_dir()
            idea_path = os.path.join(proj_dir, "business_idea.txt")
            with open(idea_path, "w", encoding="utf-8") as f:
                f.write(shared_idea)

# ---------------------------------------------------------------
# Agent Tabs Layout
# ---------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Vision & Mission Agent",
    "🔍 Research & Discovery Agent",
    "📋 Requirements Agent",
    "📅 Planning Agent",
    "🏗️ Architecture Agent",
    "💬 Harness Chat & Q&A"
])

# ---------------------------------------------------------------
# Render Tabs using modular agents
# ---------------------------------------------------------------
with tab1:
    vision_mission_agent.render(selected_model, llm_engine, server_host)

with tab2:
    research_agent.render(selected_model, llm_engine, server_host)

with tab3:
    requirements_agent.render(selected_model, llm_engine, server_host)

with tab4:
    planning_agent.render(selected_model, llm_engine, server_host)

with tab5:
    architecture_agent.render(selected_model, llm_engine, server_host)

# ---------------------------------------------------------------
# Tab 6: Harness Chat & Q&A (Interaction with Shared Memory)
# ---------------------------------------------------------------
with tab6:
    with st.container(border=True):
        st.markdown('<div class="section-label">💬 Chat Advisor (Connected to Shared Memory)</div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-helper-text">Ask questions, test assumptions, or refine your strategy using all files stored in your Shared Memory.</div>', unsafe_allow_html=True)


    chat_container = st.container()

    with st.form(key="harness_chat_form", clear_on_submit=True):
        chat_input = st.text_input("Ask advisor...", placeholder="e.g. How does our architecture align with the security requirements in constraints.txt?", key="chat_user_msg")
        send_chat = st.form_submit_button("Send to Advisor")

    if send_chat and chat_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": chat_input.strip()})
        
        with chat_container:
            st.markdown(f'<div class="chat-bubble user">{chat_input.strip()}</div>', unsafe_allow_html=True)
            
        placeholder = st.empty()
        bot_reply = ""
        
        memory_ctx = load_shared_memory()
        
        chat_messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        if memory_ctx:
            chat_messages.append({"role": "system", "content": f"Here is the contents of the Shared Memory folder for your reference:\n{memory_ctx}"})
        if st.session_state.shared_idea.strip():
            chat_messages.append({"role": "system", "content": f"The core startup idea is: {st.session_state.shared_idea.strip()}"})
            
        chat_messages.extend(st.session_state.chat_history)
        
        try:
            for chunk in stream_chat(chat_messages, selected_model, llm_engine, server_host):
                bot_reply += chunk
                placeholder.markdown(f'<div class="chat-bubble bot">{bot_reply}</div>', unsafe_allow_html=True)
            
            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            placeholder.markdown(f'<div class="chat-bubble bot" style="color:red;">❗ Error: {e}</div>', unsafe_allow_html=True)
            
        st.rerun()

    with chat_container:
        for msg in st.session_state.chat_history:
            bubble_class = "user" if msg["role"] == "user" else "bot"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{msg["content"]}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.markdown("""
<div style="text-align:center; margin-top:3rem; color:#64748b; font-size:0.8rem; padding: 1.5rem 0;">
    IdeaToIndia AI Strategy Dashboard · Powered by <strong>llama.cpp / Ollama</strong> · Safe and secure local LLM processing 🔒
</div>
""", unsafe_allow_html=True)
