# Output Instructions: Architecture Summary

Produce a document with EXACTLY these sections in order:

## 🏗️ Executive Technical Overview
- 2-3 paragraph summary of the overall system design
- State the primary architectural style (e.g. microservices, serverless, monolith)
- Mention the core technology choices and why they fit the business goal

## 🔄 Inter-Lens Alignment
- Explain how Business, Application, Infrastructure, Security, and Data layers connect
- Use a numbered flow: Business Need → Application Layer → Infrastructure → Data → Security gate
- Highlight any cross-cutting concerns (e.g. auth, observability, caching)

## 🛠️ Architectural Trade-offs
- List at least 3 major trade-off decisions made (format: Decision | Chosen Path | Reason)
- Address: build vs buy, SQL vs NoSQL, serverless vs containers, monolith vs microservices

## 📅 Phase-wise Implementation Roadmap
- Phase 1 (MVP / 0-3 months): Core system, minimal infra
- Phase 2 (Growth / 3-12 months): Scale-out, observability, security hardening
- Phase 3 (Scale / 12+ months): Multi-region, advanced analytics, enterprise features

## ⚠️ Key Risks & Mitigations
- List top 3-5 technical risks with mitigation strategies

Keep tone: professional, visionary, clear. No filler content.
