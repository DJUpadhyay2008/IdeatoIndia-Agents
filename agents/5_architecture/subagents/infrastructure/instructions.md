# Output Instructions: Infrastructure Architecture Lens

Produce a document with EXACTLY these sections in order:

## ☁️ Cloud Provider & Topology
- Primary cloud provider recommendation with rationale
- Region selection strategy (India-first? Multi-region from day 1?)
- VPC design: number of VPCs, subnet breakdown (public/private/data), CIDR ranges
- NAT Gateway placement and cost implications
- Account structure (dev/staging/prod separation strategy)

## 🖥️ Compute & Container Strategy
- Compute type for each service: EC2 / Lambda / Fargate / ECS / EKS / App Engine
- Container orchestration: Kubernetes vs ECS vs serverless — with decision rationale
- Instance type recommendations for MVP (cost-optimized)
- Auto-scaling configuration: min/max instances, scale-in/scale-out triggers, cooldown
- Spot/preemptible instance strategy for non-critical workloads

## 🌐 Traffic Management & CDN
- DNS setup (Route 53 / Cloudflare) with routing policy (latency-based, weighted, failover)
- Load balancer type (ALB / NLB / Classic) and listener configuration
- CDN setup for static assets (CloudFront / Cloudflare) with cache rules
- API Gateway configuration: throttling, usage plans, CORS

## 📈 High Availability & Disaster Recovery
- Target SLA (e.g., 99.9%, 99.95%) and what infrastructure achieves it
- Multi-AZ deployment: which components and how
- Backup strategy: what is backed up, how often, retention policy
- RTO target (Recovery Time Objective) and how it is achieved
- RPO target (Recovery Point Objective) and how it is achieved
- Runbook outline for common failure scenarios

## 💰 Cost Architecture (MVP Budget)
- Estimated monthly cost breakdown by service (compute, storage, networking, managed services)
- Cost optimization levers (reserved instances, S3 tiers, Lambda vs always-on)
- Free tier usage plan for MVP launch
- Cost alert thresholds and budget alarms

Be specific with AWS/GCP/Azure service names. Include estimated cost ranges where possible.
