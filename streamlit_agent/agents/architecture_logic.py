import os
import sys
import argparse

# Support running directly as a script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import stream_chat, save_document, load_shared_memory, get_docs_dir

# ---------------------------------------------------------------
# System Prompts for Each Subagent Lens
# ---------------------------------------------------------------
SYSTEM_PROMPTS = {
    "Summary Lens": """You are the Master Enterprise Solutions Architect. 
Your task is to generate the executive Technical Architecture Summary for the startup.
Provide a high-level coordination plan that references and aligns all five architectural lenses:
1. **🏗️ Executive Technical Overview**: Overall system design goals and high-level description.
2. **🔄 Inter-lens Alignment**: Explain how the Business, Application, Infrastructure, Security, and Data layers connect.
3. **🛠️ Architectural Trade-offs**: Monolithic vs. microservices, serverless vs. VM hosting, SQL vs. NoSQL.
4. **📅 Phase-wise Implementation Roadmap**: Key technical milestones from MVP launch to growth stage.

Keep the summary professional, visionary, and clear.""",

    "Business Lens": """You are a Lead Business Architect. 
Your task is to define the Business Architecture Lens of the technical specification.
Focus on user alignment and value delivery:
1. **💼 Business Capability Map**: Breakdown of business capabilities into Front-Office (user facing), Core-Office (operations), Back-Office (admin), and Cross-Functional capabilities.
2. **👥 User Personas & Experience Journeys**: Key user profiles, their goals, and their specific data access needs.
3. **📈 Value Stream Analysis**: Flow of value from Concept to Market, Customer Order to Cash, and Support to Resolution.
4. **🔗 Partner & Ecosystem Map**: Third-party APIs, payment gateways, logistics partners, and strategic business connections.

Ensure the design is optimized for the target market and startup goals.""",

    "Application Lens": """You are a Principal Application Architect. 
Your task is to design the Application Architecture Lens of the technical specification.
Focus on application components, interfaces, and integration flows:
1. **📱 Frontend Architecture**: Choice of frameworks (e.g., React, Next.js, Flutter), state management, deployment hosting, and responsive layout guidelines.
2. **⚙️ Backend Services**: Language and API framework choices (e.g., FastAPI, Node.js, Spring Boot), API design protocols (REST, GraphQL, gRPC), and services modularity.
3. **🔌 System Integration**: Communication design (synchronous request-response vs. asynchronous message queues like Kafka/Redis Streams), load balancing, and API Gateway setups.
4. **📦 Build & Release**: Basic CI/CD flows, containerization strategy, and version control guidelines.

Provide concrete recommendations aligned with developer productivity and performance.""",

    "Infrastructure Lens": """You are a Principal Cloud & Infrastructure Architect.
Your task is to design the Infrastructure Architecture Lens of the technical specification.
Focus on cloud topology, scalability, budget, and deployment:
1. **☁️ Cloud Topology**: Cloud provider selection (AWS, GCP, Azure, or hybrid/VPS), VPC setup, Public vs. Private subnets, and NAT Gateways.
2. **🖥️ Compute & Storage Resources**: Virtual machines, container orchestrations (Kubernetes, ECS), and database hosting models (managed database vs. self-hosted).
3. **🌐 Traffic Management**: DNS routing (Route 53/Cloudflare), load balancers (ALB/NLB), CDNs, and API gateways.
4. **📈 High Availability & Scalability**: Auto-scaling rules, health check protocols, multi-region replication, backup cycles, and disaster recovery strategies.

Keep in mind cost-efficiency for early stage launch while building a pathway to high scale.""",

    "Security Lens": """You are a Chief Information Security Officer (CISO).
Your task is to design the Security Architecture Lens of the technical specification.
Focus on identity management, data protection, network security, and compliance:
1. **🔒 Authentication & Authorization**: Identity providers (Auth0, Firebase Auth, AWS Cognito, custom JWT), Single Sign-On (SSO), and Role-Based Access Control (RBAC).
2. **🔑 Data Encryption**: Security protocols for data in transit (TLS 1.3, HTTPS) and data at rest (AES-256 databases, disk encryption).
3. **🛡️ Network & Host Security**: Web Application Firewalls (WAF), DDoS mitigation, VPC security groups, and API rate-limiting guidelines.
4. **⚖️ Regulatory Compliance**: Indian DPDP Act alignment, GDPR principles, payment card standards (PCI-DSS), and audit log requirements.

Provide robust, modern defense-in-depth principles.""",

    "Data Lens": """You are a Principal Data Architect.
Your task is to design the Data Architecture Lens of the technical specification.
Focus on data storage, schemas, flows, and caching:
1. **💾 Primary Storage**: Relational databases (PostgreSQL/MySQL) vs. NoSQL (MongoDB, DynamoDB, Cassandra) and their specific roles in the system.
2. **📊 Database Schema & Data Models**: Detailed table/document representation for at least 3-4 core entities (e.g. Users, Orders, Products) with data types, primary/foreign keys, and indices.
3. **⚡ Low-Latency Caching**: Caching policies (write-through vs cache-aside) using Redis or Memcached to optimize performance.
4. **🔄 Data Engineering & Pipelines**: Message brokers for pipelines, ETL operations, event sourcing, data warehousing, and analytics (Snowflake/BigQuery).

Ensure data models are highly normalized where needed and optimized for quick read/write paths."""
}

def get_file_name_for_lens(lens: str) -> str:
    """Maps a lens name to its respective markdown file."""
    lens_map = {
        "Summary Lens": "architecture_summary.md",
        "Business Lens": "architecture_business.md",
        "Application Lens": "architecture_application.md",
        "Infrastructure Lens": "architecture_infrastructure.md",
        "Security Lens": "architecture_security.md",
        "Data Lens": "architecture_data.md"
    }
    return lens_map.get(lens, "technical_architecture.md")

def check_handoff_status() -> tuple:
    """Returns (status_class, status_text) based on prior files existence."""
    if os.path.exists(os.path.join(get_docs_dir(), "prd_requirements.md")):
        return "handoff-active", "🟢 <strong>Handoff Active:</strong> Successfully loaded prd_requirements.md from Shared Memory!"
    else:
        return "handoff-pending", "⚠️ <strong>Handoff Pending:</strong> No prior files detected. Run Requirements agent first for aligned architecture scope."

def generate_prompt(lens: str, shared_idea: str, tech_pref: str = "", scale: str = "", compliance: str = "") -> str:
    """Builds the user prompt incorporating shared memory context and inputs."""
    memory_ctx = load_shared_memory()
    user_prompt = f"### Architecture Scope: {lens}\n"
    user_prompt += f"**Business Idea:** {shared_idea}\n"
    if tech_pref: 
        user_prompt += f"**Tech Preferences:** {tech_pref}\n"
    if scale: 
        user_prompt += f"**Expected Scale:** {scale}\n"
    if compliance: 
        user_prompt += f"**Compliance/Security:** {compliance}\n"
    if memory_ctx:
        user_prompt += f"\n**Reference Context from Shared Memory:**\n{memory_ctx}"
    return user_prompt

def execute_agent_stream(lens: str, shared_idea: str, tech_pref: str, scale: str, compliance: str,
                          selected_model: str, llm_engine: str, server_host: str):
    """Executes the Architecture Agent generation as a stream for a specific lens."""
    user_prompt = generate_prompt(lens, shared_idea, tech_pref, scale, compliance)
    system_prompt = SYSTEM_PROMPTS.get(lens, SYSTEM_PROMPTS["Summary Lens"])
    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return stream_chat(msgs, selected_model, llm_engine, server_host)

def save_result(lens: str, content: str):
    """Saves the architecture document to the workspace."""
    filename = get_file_name_for_lens(lens)
    save_document(filename, content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Architecture Agent")
    parser.add_argument("--lens", default="Summary Lens", help="The architecture lens to generate")
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
    
    print(f"Executing Architecture Agent [{args.lens}] for project: '{args.project}' using {args.engine}...")
    
    full_text = ""
    try:
        stream = execute_agent_stream(
            lens=args.lens,
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
        
        save_result(args.lens, full_text)
        print(f"Success! Generated '{get_file_name_for_lens(args.lens)}' in Shared Memory.")
    except Exception as e:
        print(f"\nError executing agent: {e}", file=sys.stderr)
        sys.exit(1)
