# Output Instructions: Business Architecture Lens

Produce a document with EXACTLY these sections in order:

## 💼 Business Capability Map
Organize capabilities into 4 layers:
- **Front-Office** (customer-facing): list 4-6 capabilities
- **Core-Office** (operations): list 4-6 capabilities
- **Back-Office** (admin/finance/HR): list 3-5 capabilities
- **Cross-Functional** (auth, notifications, analytics): list 3-4 capabilities

Each capability: name + one-line description + priority (P1/P2/P3)

## 👥 User Personas & Experience Journeys
Define 3-4 user personas:
- Persona name + role
- Primary goal
- Pain points (2-3)
- Key system touchpoints (what features they use)
- Data they produce and consume

## 📈 Value Stream Analysis
Map 3 core value streams:
1. **Concept to Market**: How the business idea becomes a product
2. **Customer Order to Cash**: How a user converts and pays
3. **Support to Resolution**: How issues are handled end-to-end

For each stream: list the 5-7 steps and the system component responsible

## 🔗 Partner & Ecosystem Map
- List external systems and partners (APIs, payment gateways, logistics, analytics)
- For each: name, purpose, integration type (webhook/REST/SDK), criticality (core/optional)

## 📊 Business KPIs → System Features Mapping
List 5-6 business KPIs and map each to the specific system feature that enables it.
Format: KPI | Target | Enabling Feature | Architecture Component

Keep language business-friendly but technically grounded.
