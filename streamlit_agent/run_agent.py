#!/usr/bin/env python3
import os
import sys
import argparse

# Force streamlit_agent to be in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.vision_mission_logic import execute_agent_stream as run_vm, save_result as save_vm
from agents.research_logic import execute_agent_stream as run_res, save_result as save_res
from agents.requirements_logic import execute_agent_stream as run_req, save_result as save_req
from agents.planning_logic import execute_agent_stream as run_plan, save_result as save_plan
from agents.architecture_logic import execute_agent_stream as run_arch, save_result as save_arch

def main():
    parser = argparse.ArgumentParser(
        description="IdeaToIndia — Standalone Strategy Agent Runner\n"
                    "Execute any of the business analysis agents directly from your terminal.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Global Configs
    parser.add_argument("--agent", required=True, 
                        choices=["vision_mission", "research", "requirements", "planning", "architecture"],
                        help="The strategy agent to run.")
    parser.add_argument("--idea", required=True, help="The startup/business idea description.")
    parser.add_argument("--project", default="default_project", help="Workspace project folder name (defaults to default_project).")
    parser.add_argument("--engine", default="Google Gemini API", 
                        choices=["Ollama", "Google Gemini API", "llama.cpp (llama-server)"],
                        help="LLM Engine to use (defaults to 'Google Gemini API').")
    parser.add_argument("--model", default="", help="LLM model name (defaults based on engine choice).")
    parser.add_argument("--host", default="", help="Local host URL for llama.cpp or Ollama (if applicable).")

    # Agent Specific Options
    # Vision & Mission
    parser.add_argument("--industry", default="", help="[Vision/Mission] Industry / sector")
    parser.add_argument("--audience", default="", help="[Vision/Mission] Primary target audience")
    parser.add_argument("--principles", default="", help="[Vision/Mission] Brand values / principles")
    
    # Research
    parser.add_argument("--competitors", default="", help="[Research] Known competitors / alternatives")
    parser.add_argument("--region", default="", help="[Research] Target location / region")
    parser.add_argument("--details", default="", help="[Research] Specific market questions / context")
    
    # Requirements
    parser.add_argument("--roles", default="", help="[Requirements] User roles / persona types")
    parser.add_argument("--features", default="", help="[Requirements] Key features / modules (MVP Scope)")
    parser.add_argument("--compliance", default="", help="[Requirements] Regulatory or compliance constraints")
    
    # Planning
    parser.add_argument("--timeline", default="6 Months", help="[Planning] Launch timeline goal")
    parser.add_argument("--budget", default="", help="[Planning] Estimated initial capital")
    parser.add_argument("--constraints", default="", help="[Planning] Operational / team constraints")
    
    # Architecture
    parser.add_argument("--tech", default="", help="[Architecture] Tech stack preferences")
    parser.add_argument("--scale", default="", help="[Architecture] Expected traffic / user base")
    # (uses --compliance from requirements as well for security/compliance)

    args = parser.parse_args()

    # Set project environment variable
    os.environ["CURRENT_PROJECT"] = args.project

    # Set up defaults for engine
    engine = args.engine
    host = args.host
    model = args.model

    if engine == "Google Gemini API":
        if not model:
            model = "gemini-2.5-flash"
        # Make sure API key is set
        if not os.environ.get("GEMINI_API_KEY"):
            print("⚠️ Warning: GEMINI_API_KEY environment variable is not set.\n"
                  "Please set it using: export GEMINI_API_KEY='your_api_key'", file=sys.stderr)
    elif engine == "Ollama":
        if not model:
            model = "gemma4:e2b"
        if not host:
            host = "http://localhost:11434"
    else: # llama.cpp
        if not model:
            model = "gemma4"
        if not host:
            host = "http://localhost:8080"

    print("=" * 60)
    print(f"🚀 Executing Agent: {args.agent.upper()}")
    print(f"📁 Project Workspace: {args.project}")
    print(f"🤖 AI Engine: {engine} (Model: {model})")
    print("=" * 60)

    try:
        if args.agent == "vision_mission":
            stream = run_vm(args.idea, args.industry, args.audience, args.principles, model, engine, host)
            save_fn = save_vm
        elif args.agent == "research":
            stream = run_res(args.idea, args.competitors, args.region, args.details, model, engine, host)
            save_fn = save_res
        elif args.agent == "requirements":
            stream = run_req(args.idea, args.roles, args.features, args.compliance, model, engine, host)
            save_fn = save_req
        elif args.agent == "planning":
            stream = run_plan(args.idea, args.timeline, args.budget, args.constraints, model, engine, host)
            save_fn = save_plan
        elif args.agent == "architecture":
            stream = run_arch(args.idea, args.tech, args.scale, args.compliance, model, engine, host)
            save_fn = save_arch
        else:
            raise ValueError(f"Unknown agent: {args.agent}")

        full_text = ""
        for chunk in stream:
            full_text += chunk
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n" + "=" * 60)
        
        save_fn(full_text)
        print(f"✅ Success! Generated output has been saved to the '{args.project}' project directory.")
    except Exception as e:
        print(f"\n❌ Error executing agent: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
