# Output Instructions: Application Architecture Lens

Produce a document with EXACTLY these sections in order:

## 📱 Frontend Architecture
- Framework recommendation with justification (React/Next.js/Flutter etc.)
- State management approach (Redux, Zustand, Context API, Jotai)
- Hosting and deployment target (Vercel, Netlify, S3+CloudFront)
- Responsive/mobile strategy
- Key UI components or screens to build (at least 5 named components)

## ⚙️ Backend Services
- Language and framework choice with rationale
- API design protocol (REST / GraphQL / gRPC) — when and why
- Service breakdown: list each service/module with its responsibility
- Authentication middleware approach
- Error handling and logging strategy

## 🔌 System Integration & Communication
- Synchronous vs asynchronous communication map
- Internal service communication (HTTP / message queue / event bus)
- External API integrations (payment, maps, SMS, email, etc.)
- API Gateway setup (Kong, AWS API GW, Nginx)
- Load balancer configuration

## 📦 Build, Test & Release Pipeline
- CI/CD tool choice (GitHub Actions, GitLab CI, etc.)
- Pipeline stages: lint → unit test → integration test → build → deploy
- Containerization strategy (Docker, multi-stage builds)
- Branching strategy (GitFlow, trunk-based)
- Feature flag / rollback mechanism

Provide specific, concrete technology names. No vague suggestions.
