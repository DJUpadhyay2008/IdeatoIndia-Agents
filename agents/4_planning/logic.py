import os
import sys
import argparse

# Import from common package
from common import stream_chat, save_document, load_shared_memory, get_docs_dir, save_document_with_metadata

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

def check_handoff_status() -> tuple:
    """Returns (status_class, status_text) based on prior files existence."""
    if os.path.exists(os.path.join(get_docs_dir(), "technical_architecture.md")):
        return "handoff-active", "🟢 <strong>Handoff Active:</strong> Successfully loaded technical_architecture.md from Shared Memory!"
    else:
        return "handoff-pending", "⚠️ <strong>Handoff Pending:</strong> No prior files detected. Run Architecture agent first for aligned planning scope."

def generate_prompt(shared_idea: str, timeline: str = "6 Months", budget: str = "", constraints: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"**Business Idea:** {shared_idea}\n"
    if timeline: 
        user_prompt += f"**Timeline Goal:** {timeline}\n"
    if budget: 
        user_prompt += f"**Budget Details:** {budget}\n"
    if constraints: 
        user_prompt += f"**Operational Constraints:** {constraints}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(shared_idea: str, timeline: str, budget: str, constraints: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """Executes the Planning Agent generation as a stream."""
    user_prompt = generate_prompt(shared_idea, timeline, budget, constraints)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(content: str, selected_model: str = None, llm_engine: str = None, server_host: str = None):
    """Saves the planning document to the workspace."""
    save_document_with_metadata("launch_plan.md", content, "Launch Plan & Roadmap", selected_model, llm_engine, server_host)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Planning Agent")
    parser.add_argument("--idea", required=True, help="The startup/business idea description")
    parser.add_argument("--timeline", default="6 Months", help="Launch timeline goal")
    parser.add_argument("--budget", default="", help="Estimated initial capital")
    parser.add_argument("--constraints", default="", help="Operational / team constraints")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--engine", default="Google Gemini API", choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"], help="LLM Engine")
    parser.add_argument("--host", default="http://localhost:8080", help="Local host URL for llama.cpp or Ollama")
    
    args = parser.parse_args()
    os.environ["CURRENT_PROJECT"] = args.project
    
    print(f"Executing Planning Agent for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            shared_idea=args.idea,
            timeline=args.timeline,
            budget=args.budget,
            constraints=args.constraints,
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
        print("Success! Generated 'launch_plan.md' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
