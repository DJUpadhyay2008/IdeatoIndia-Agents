import os
import sys
import argparse

# Support running directly as a script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

SYSTEM_PROMPT = """You are a Solutions Architect with 15+ years of experience designing robust, scalable startup architectures.

Using the provided business idea and optional context, you will produce EXACTLY the following structured output:

## 🛠️ Technical Stack Recommendations
Choose highly compatible, cost-efficient, modern stacks (e.g. MERN, Next.js + Supabase, FastAPI + Postgres). For each tier, justify your choice:
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

def check_handoff_status() -> bool:
    """Returns True if the required prior prd_requirements.md exists."""
    return os.path.exists(os.path.join(get_docs_dir(), "prd_requirements.md"))

def generate_prompt(shared_idea: str, tech_pref: str = "", scale: str = "", compliance: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"**Business Idea:** {shared_idea}\n"
    if tech_pref: 
        user_prompt += f"**Tech Preferences:** {tech_pref}\n"
    if scale: 
        user_prompt += f"**Expected Scale:** {scale}\n"
    if compliance: 
        user_prompt += f"**Compliance/Security:** {compliance}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(shared_idea: str, tech_pref: str, scale: str, compliance: str,
                         selected_model: str, llm_engine: str, server_host: str):
    """Executes the Architecture Agent generation as a stream."""
    user_prompt = generate_prompt(shared_idea, tech_pref, scale, compliance)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(content: str):
    """Saves the architecture document to the workspace."""
    save_document("technical_architecture.md", content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Architecture Agent")
    parser.add_argument("--idea", required=True, help="The startup/business idea description")
    parser.add_argument("--tech", default="", help="Tech stack preferences")
    parser.add_argument("--scale", default="", help="Expected traffic / user base")
    parser.add_argument("--compliance", default="", help="Compliance / safety needs")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--engine", default="Google Gemini API", choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"], help="LLM Engine")
    parser.add_argument("--host", default="http://localhost:8080", help="Local host URL for llama.cpp or Ollama")
    
    args = parser.parse_args()
    
    os.environ["CURRENT_PROJECT"] = args.project
    
    print(f"Executing Architecture Agent for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            shared_idea=args.idea,
            tech_pref=args.tech,
            scale=args.scale,
            compliance=args.compliance,
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
        print("Success! Generated 'technical_architecture.md' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
