import os
import sys
import argparse

# Import from common package
from common import stream_chat, save_document, load_shared_memory, get_docs_dir, save_document_with_metadata

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

def check_handoff_status() -> tuple:
    """Returns (status_class, status_text) based on prior files existence."""
    if os.path.exists(os.path.join(get_docs_dir(), "vision_mission.md")):
        return "handoff-active", "🟢 <strong>Handoff Active:</strong> Successfully loaded vision_mission.md from Shared Memory!"
    else:
        return "handoff-pending", "⚠️ <strong>Handoff Pending:</strong> No prior files detected. Run Vision & Mission agent first for aligned research scope."

def generate_prompt(shared_idea: str, competitors: str = "", region: str = "", market_details: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"**Business Idea:** {shared_idea}\n"
    if competitors: 
        user_prompt += f"**Competitors:** {competitors}\n"
    if region: 
        user_prompt += f"**Target Region:** {region}\n"
    if market_details: 
        user_prompt += f"**Market Context/Questions:** {market_details}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(shared_idea: str, competitors: str, region: str, market_details: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """Executes the Research Agent generation as a stream."""
    user_prompt = generate_prompt(shared_idea, competitors, region, market_details)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(content: str, selected_model: str = None, llm_engine: str = None, server_host: str = None):
    """Saves the market research document to the workspace."""
    save_document_with_metadata("market_research.md", content, "Market Research", selected_model, llm_engine, server_host)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Research Agent")
    parser.add_argument("--idea", required=True, help="The startup/business idea description")
    parser.add_argument("--competitors", default="", help="Known competitors / alternatives")
    parser.add_argument("--region", default="", help="Target location / region")
    parser.add_argument("--details", default="", help="Specific market questions / context")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--engine", default="Google Gemini API", choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"], help="LLM Engine")
    parser.add_argument("--host", default="http://localhost:8080", help="Local host URL for llama.cpp or Ollama")
    
    args = parser.parse_args()
    os.environ["CURRENT_PROJECT"] = args.project
    
    print(f"Executing Research Agent for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            shared_idea=args.idea,
            competitors=args.competitors,
            region=args.region,
            market_details=args.details,
            selected_model=args.model,
            llm_engine=args.engine,
            server_host=args.host
        )
        for chunk in stream:
            full_text += chunk
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n")
        
        save_result(full_text, args.model, args.engine, args.host)
        print("Success! Generated 'market_research.md' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
