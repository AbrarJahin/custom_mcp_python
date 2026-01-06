# MCP Server – Tool & Data Gateway for Agent-Based LLM Platform

This document describes the design, responsibilities, and integration details of an **MCP (Model Context Protocol) Server** used alongside an existing **FastAPI-based agent orchestration system**.

The MCP Server acts as a **centralized, permissioned tool and data access layer** for LLM agents. It standardizes how agents access databases, files, knowledge bases, web data, and external APIs—without embedding tool logic inside each agent.

---

## Table of Contents

- Overview
- Why an MCP Server is Needed
- Responsibilities of the MCP Server
- What the MCP Server Does NOT Do
- System Architecture
- How MCP Communicates with FastAPI
- Agent Interaction Model
- Tool Categories Exposed by MCP
- Security and Permission Model
- Observability and Auditing
- Failure Handling and Safety Limits
- Deployment Model
- Scaling Strategy
- Summary

---

## Overview

As the system grows to include:
- many agents,
- agent-to-agent asynchronous calls,
- mobile and web clients,
- multiple data sources and APIs,

a dedicated **tool gateway** becomes necessary.

The MCP Server fulfills this role by providing a **stable contract** between agents and the external world.

---

## Why an MCP Server is Needed

Without MCP:
- Each agent implements its own database, file, and web logic
- Security rules are duplicated or inconsistent
- Tool usage is difficult to audit
- Changes to tools require agent code changes

With MCP:
- Tools are defined once
- Access is centrally controlled
- Logging and tracing are consistent
- Agents remain lightweight and focused on reasoning

MCP improves **integration scalability**, not raw LLM throughput.

---

## Responsibilities of the MCP Server

The MCP Server is responsible for:

1. Exposing tools through a standardized protocol
2. Enforcing permissions and policies per agent
3. Applying safety limits and allowlists
4. Auditing all tool usage
5. Providing observability for debugging and compliance

---

## What the MCP Server Does NOT Do

The MCP Server does NOT:
- run LLM inference
- generate embeddings
- orchestrate agents
- expose APIs to end users
- manage background ingestion jobs

These responsibilities remain with:
- FastAPI (orchestration, API layer)
- Ollama / vLLM (inference)
- Celery (background ingestion)

---

## System Architecture

High-level flow:

Clients (Web / Mobile)
→ FastAPI API Server
→ Planner Agent
→ Sub-Agents (2–5 async)
→ MCP Server (tools)
→ Databases / Files / KB / Web / APIs

The MCP Server sits **beside** the LLM servers, not in front of them.

---

## How MCP Communicates with FastAPI

- FastAPI does not proxy MCP calls
- FastAPI spawns agents and provides context
- Agents communicate directly with MCP using MCP protocol

FastAPI provides:
- authentication
- request/session identifiers
- agent role information
- short-lived MCP access tokens

---

## Agent Interaction Model

Agents:
- reason using LLMs
- request data/actions via MCP tools
- never access databases or files directly

Examples:
- Research Agent → web.search, web.fetch
- RAG Agent → kb.search
- DB Agent → db.read_*
- Ingest Agent → files.read, kb.upsert

This keeps agents deterministic and auditable.

---

## Tool Categories Exposed by MCP

### File & Document Tools
- Read text files
- Extract PDF content
- Return metadata and page mappings

### Knowledge Base Tools
- Vector search (Qdrant)
- Filtered retrieval
- Controlled upserts (restricted)

### Database Tools
- Structured read operations
- Limited write operations
- No unrestricted raw SQL by default

### Web Tools
- Search engines
- Page fetching
- Content sanitization

### External API Tools
- Allowlisted integrations
- Centralized secrets management

---

## Security and Permission Model

Security is enforced at multiple layers.

### FastAPI Layer
- User authentication
- Tenant isolation
- Request-level rate limits

### MCP Layer
- Per-agent tool allowlists
- Read vs write separation
- Network egress restrictions
- Payload size and timeout limits

Example permissions:

Planner Agent: no tools  
Research Agent: web tools only  
RAG Agent: KB search only  
DB Agent: DB read only  
Ingest Agent: file read + KB write  

---

## Observability and Auditing

Every MCP tool call records:
- request ID
- agent role
- tool name
- execution duration
- success or failure

Integrated with:
- OpenTelemetry
- Metrics (Prometheus)
- Tracing (Jaeger / Tempo)

This enables debugging, compliance audits, and performance tuning.

---

## Failure Handling and Safety Limits

The MCP Server enforces:
- strict timeouts
- maximum payload sizes
- retries only for safe operations
- clear error contracts
- circuit breaking for unstable dependencies

Agents must handle tool failures gracefully.

---

## Deployment Model

### Minimal Deployment
- MCP Server (stateless)
- Redis (optional: caching, rate limits)
- Network access to DB, KB, file storage

### Scaling
- MCP Server scales horizontally
- No shared state except Redis
- Independent from LLM scaling

---

## Scaling Strategy

MCP scales:
- number of agents
- number of tools
- number of integrations

LLM throughput is scaled separately using:
- vLLM
- batching
- caching
- queueing

---

## Summary

The MCP Server is:
- a standardized tool gateway
- a security and policy boundary
- an audit and observability layer
- an enabler for large agent ecosystems

It complements FastAPI and LLM servers rather than replacing them.

In this architecture:
- FastAPI orchestrates
- Agents reason
- LLMs generate
- MCP tools act
- Background workers ingest

Each layer stays focused, testable, and scalable.
