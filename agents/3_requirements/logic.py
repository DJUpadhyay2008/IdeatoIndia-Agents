import os
import sys
import argparse

# Import from common package
from common import stream_chat, save_document, load_shared_memory, get_docs_dir

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

def get_handoff_files_present():
    """Returns a tuple of (has_vision_mission, has_market_research)."""
    has_vm = os.path.exists(os.path.join(get_docs_dir(), "vision_mission.md"))
    has_res = os.path.exists(os.path.join(get_docs_dir(), "market_research.md"))
    return has_vm, has_res

def generate_prompt(shared_idea: str, target_roles: str = "", key_features: str = "", compliance_requirements: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"**Business Idea:** {shared_idea}\n"
    if target_roles: 
        user_prompt += f"**User Roles:** {target_roles}\n"
    if key_features: 
        user_prompt += f"**Core Features/Modules:** {key_features}\n"
    if compliance_requirements: 
        user_prompt += f"**Compliance/NFR Constraints:** {compliance_requirements}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(shared_idea: str, target_roles: str, key_features: str, compliance_requirements: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """Executes the Requirements Agent generation as a stream."""
    user_prompt = generate_prompt(shared_idea, target_roles, key_features, compliance_requirements)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(content: str):
    """Saves the requirements document to the workspace."""
    save_document("prd_requirements.md", content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Requirements Agent")
    parser.add_argument("--idea", required=True, help="The startup/business idea description")
    parser.add_argument("--roles", default="", help="User roles / persona types")
    parser.add_argument("--features", default="", help="Key features / modules (MVP Scope)")
    parser.add_argument("--compliance", default="", help="Regulatory or compliance constraints")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--engine", default="Google Gemini API", choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"], help="LLM Engine")
    parser.add_argument("--host", default="http://localhost:8080", help="Local host URL for llama.cpp or Ollama")
    
    args = parser.parse_args()
    os.environ["CURRENT_PROJECT"] = args.project
    
    print(f"Executing Requirements Agent for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            shared_idea=args.idea,
            target_roles=args.roles,
            key_features=args.features,
            compliance_requirements=args.compliance,
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
        print("Success! Generated 'prd_requirements.md' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
