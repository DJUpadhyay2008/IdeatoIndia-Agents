import os
import sys
import argparse

# Support running directly as a script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def generate_prompt(shared_idea: str, industry: str = "", audience: str = "", principles: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"**Business Idea:** {shared_idea}\n"
    if industry: 
        user_prompt += f"**Industry:** {industry}\n"
    if audience: 
        user_prompt += f"**Target Audience:** {audience}\n"
    if principles: 
        user_prompt += f"**Core Values:** {principles}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(shared_idea: str, industry: str, audience: str, principles: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """Executes the Vision & Mission Agent generation as a stream."""
    user_prompt = generate_prompt(shared_idea, industry, audience, principles)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(content: str):
    """Saves the vision and mission document to the workspace."""
    save_document("vision_mission.md", content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Vision & Mission Agent")
    parser.add_argument("--idea", required=True, help="The startup/business idea description")
    parser.add_argument("--industry", default="", help="Industry / sector")
    parser.add_argument("--audience", default="", help="Primary target audience")
    parser.add_argument("--principles", default="", help="Brand values / principles")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--engine", default="Google Gemini API", choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"], help="LLM Engine")
    parser.add_argument("--host", default="http://localhost:8080", help="Local host URL for llama.cpp or Ollama")
    
    args = parser.parse_args()
    
    # Configure project workspace environment variable
    os.environ["CURRENT_PROJECT"] = args.project
    
    print(f"Executing Vision & Mission Agent for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            shared_idea=args.idea,
            industry=args.industry,
            audience=args.audience,
            principles=args.principles,
            selected_model=args.model,
            llm_engine=args.engine,
            server_host=args.host
        )
        for chunk in stream:
            full_text += chunk
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n")
        
        save_result(full_text)
        print("Success! Generated 'vision_mission.md' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
