# Output Instructions: Security Architecture Lens

Produce a document with EXACTLY these sections in order:

## 🔒 Authentication & Authorization
- Identity provider recommendation (Auth0 / AWS Cognito / Firebase / custom JWT) with rationale
- Token strategy: JWT structure, expiry policy, refresh token handling
- SSO strategy (if applicable)
- RBAC design: list roles and their permission scopes
- Session management approach (stateless vs stateful)

## 🔑 Data Encryption Strategy
- **In Transit**: protocols (TLS 1.3, HTTPS), certificate management, where enforced
- **At Rest**: encryption algorithm (AES-256), which data stores are encrypted, key management
- **In Use**: any sensitive fields requiring field-level encryption (PII, payment data)
- Secrets management: how API keys, DB passwords, env vars are stored and rotated

## 🛡️ Network & Host Security
- WAF configuration: rules, OWASP Top 10 coverage
- DDoS mitigation strategy
- VPC design: public/private subnet security rules
- API rate limiting: per-user, per-IP, per-endpoint limits
- Container/runtime security (image scanning, Falco, seccomp profiles)

## ⚖️ Regulatory Compliance
- Map each applicable regulation (DPDP, GDPR, PCI-DSS) to specific system controls
- Data residency requirements and how they are enforced
- Consent management implementation
- Right to erasure / data subject access request (DSAR) workflow
- Audit log requirements: what is logged, retention period, immutability

## 🚨 Threat Model & Incident Response
- Top 5 threat vectors for this system with STRIDE categorization
- Detection mechanisms for each threat
- Incident response playbook outline (detect → contain → eradicate → recover)
- Security monitoring stack (SIEM, alerting, dashboards)

Be specific, actionable, and compliance-aware.
