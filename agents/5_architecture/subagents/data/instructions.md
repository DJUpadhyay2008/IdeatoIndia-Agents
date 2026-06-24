# Output Instructions: Data Architecture Lens

Produce a document with EXACTLY these sections in order:

## 💾 Primary Storage Strategy
- Primary database recommendation (relational vs NoSQL) with detailed rationale
- Secondary databases if needed (e.g. Redis for cache, Elasticsearch for search)
- Hosting model: managed service (RDS, Supabase, PlanetScale) vs self-hosted
- Connection pooling strategy (PgBouncer, RDS Proxy)
- Read replica setup for scaling reads

## 📊 Database Schema & Data Models
Design schemas for the 4-6 most important entities in the system.

For each entity, provide:
- Table/collection name
- Fields: name | type | constraints (PK, FK, Unique, Not Null, Index)
- Relationships (one-to-many, many-to-many with junction table)
- Indexing strategy for frequent query patterns

Example format:
```
TABLE: users
- id: UUID (PK)
- email: VARCHAR(255) (UNIQUE, NOT NULL, INDEX)
- created_at: TIMESTAMP (NOT NULL, DEFAULT NOW())
```

## ⚡ Caching Architecture
- Cache layer technology (Redis / Memcached)
- Caching strategy per use case: write-through vs cache-aside vs read-through
- TTL policies for different data types
- Cache invalidation strategy
- Redis data structures used (String, Hash, Sorted Set, List) and why

## 🔄 Data Pipelines & Event Streams
- Event streaming platform (Kafka / Kinesis / SQS) — if needed and why
- Key events/topics and their producers/consumers
- ETL/ELT pipelines: what data moves where and when
- Analytics data flow: OLTP → data warehouse path
- Real-time vs batch processing decision for each pipeline

## 🗄️ Data Governance & Lifecycle
- PII fields identified in each table + masking/encryption approach
- Data retention policy per entity (how long kept, deletion trigger)
- Backup schedule and restore procedure
- Migration strategy for future schema changes (zero-downtime approach)
- Multi-tenancy isolation approach if applicable

Be precise with data types, constraints, and index names.
