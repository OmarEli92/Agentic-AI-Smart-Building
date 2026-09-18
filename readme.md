# Agentic AI Smart Building

This project was developed as part of my Master's thesis and explores the use of **Agentic AI for Smart Building management**.

The system allows a Facility Manager to interact with a building using natural language by combining BIM information, IoT telemetry, comfort assessment, planning, human approval, deterministic safety validation and actuator control.

Two orchestration strategies are supported:

* **Explicit LangGraph Workflow**
* **Full ReAct Agent**

Both use the same underlying Smart Building services. The main difference is how the execution flow is decided.

## Table of Contents

* [Quick Start](#quick-start)
* [Environment Configuration](#environment-configuration)
* [Main Configuration Options](#main-configuration-options)
* [Docker Infrastructure](#docker-infrastructure)
* [Running the Application](#running-the-application)
* [Architecture](#architecture)
* [Proactive Monitoring](#proactive-monitoring)
* [Observability](#observability)
* [Evaluation](#evaluation)
* [Main Technologies](#main-technologies)

---

# Quick Start

## 1. Clone the repository

```powershell
git clone https://github.com/OmarEli92/Agentic-AI-Smart-Building
cd Agentic-AI-Smart-Building
```

## 2. Create the virtual environment

Python 3.12 is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Install the project

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

All Python dependencies are defined in:

```text
pyproject.toml
```

## 4. Create the environment files

The repository contains three example environment files:

```text
.env.example
.env.cache.example
.env.langfuse.example
```

Create the local versions with:

```powershell
Copy-Item .env.example .env
Copy-Item .env.cache.example .env.cache
Copy-Item .env.langfuse.example .env.langfuse
```

The three files have different responsibilities:

```text
.env
Application configuration

.env.cache
Redis infrastructure configuration

.env.langfuse
Langfuse infrastructure configuration
```

Do not commit real credentials to Git.

## 5. Load the building model

GraphDB:

```powershell
python scripts/load_graphdb_ontology.py
```

Neo4j, if required:

```powershell
python scripts/load_neo4j_ontology.py
```

## 6. Create ThingsBoard devices

```powershell
python scripts/add_device_thingsboard.py
```

## 7. Populate ThingsBoard telemetry

```powershell
python scripts/populate_thingsboard.py
```

---

# Environment Configuration

The main application configuration is stored in:

```text
.env
```

It contains settings for:

* LLM provider
* agent orchestration
* GraphDB
* ThingsBoard
* MCP
* actuation
* BIM cache
* Langfuse client
* proactive monitoring
* SQLite persistence

Redis infrastructure variables are stored in:

```text
.env.cache
```

Langfuse infrastructure variables are stored in:

```text
.env.langfuse
```

Application credentials for Langfuse, such as the public key, secret key and server URL, remain in the main `.env`.

---

# Main Configuration Options

## Agent Orchestration

LangGraph Workflow:

```env
AGENT_ORCHESTRATION=workflow
```

Full ReAct:

```env
AGENT_ORCHESTRATION=full_react
```

In Workflow mode, the software defines the execution sequence.

In Full ReAct mode, the LLM dynamically selects tools and decides the sequence of operations.

## ThingsBoard Integration

REST:

```env
THINGSBOARD_INTEGRATION=rest
```

MCP:

```env
THINGSBOARD_INTEGRATION=mcp
```

REST communicates directly with ThingsBoard APIs.

MCP exposes ThingsBoard capabilities through a Model Context Protocol server.

## Actuation Backend

Telemetry simulation:

```env
THINGSBOARD_ACTUATION_BACKEND=telemetry
```

ThingsBoard RPC:

```env
THINGSBOARD_ACTUATION_BACKEND=rpc
```

The telemetry mode is useful for simulation and experiments.

RPC can send commands to actual devices through ThingsBoard Server Side RPC.

## BIM Cache

Without cache:

```env
BIM_CACHE_BACKEND=none
```

With Redis:

```env
BIM_CACHE_BACKEND=redis
```

The Redis cache reduces repeated BIM sensor and actuator resolution operations.

---

# Docker Infrastructure

The project uses three separate Docker Compose files:

```text
docker-compose.yml
docker-compose.cache.yml
docker-compose.langfuse.yml
```

Their purpose is:

```text
docker-compose.yml
Main Smart Building infrastructure

docker-compose.cache.yml
Optional Redis cache

docker-compose.langfuse.yml
Langfuse observability infrastructure
```

This makes it possible to start only the services required by the current configuration.

## Main Infrastructure

```powershell
docker compose `
  -f docker-compose.yml `
  --env-file .env `
  up -d
```

## Redis

Required only when:

```env
BIM_CACHE_BACKEND=redis
```

Start it with:

```powershell
docker compose `
  -f docker-compose.cache.yml `
  --env-file .env.cache `
  up -d
```

## Langfuse

```powershell
docker compose `
  -f docker-compose.langfuse.yml `
  --env-file .env.langfuse `
  up -d
```

The web interface is available by default at:

```text
http://localhost:3000
```

To stop a stack, use the corresponding command with:

```powershell
down
```

Avoid `down -v` unless persistent Docker volumes should intentionally be deleted.

---

# Running the Application

## CLI

```powershell
python -m agentic_bim_iot.main
```

The selected architecture depends on:

```env
AGENT_ORCHESTRATION
```

## Streamlit Interface

```powershell
python -m streamlit run src/agentic_bim_iot/streamlit_app.py
```

The Streamlit interface allows the Facility Manager to:

* submit natural language requests
* inspect responses
* view notifications
* inspect pending proposals
* approve or reject proposals
* interact with actuator commands

## Proactive Monitor

Run the proactive monitor in another terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m agentic_bim_iot.proactive_main
```

A typical setup therefore uses:

```text
Terminal 1 → Streamlit

Terminal 2 → Proactive Monitor
```

---

# Architecture

The two orchestration strategies share the same application services and infrastructure.

```text
                         User
                          ↓
                  CLI / Streamlit UI
                          ↓
               Agent Orchestration
                ┌────────┴────────┐
                │                 │
           LangGraph           Full ReAct
           Workflow              Agent
                │                 │
                └────────┬────────┘
                         ↓
                Application Services
                         ↓
        ┌────────────────┼────────────────┐
        │                │                │
        ↓                ↓                ↓
   BIM / Semantic   IoT / Telemetry   Comfort Engine
      GraphDB          ThingsBoard
        │                │
        └────────┬───────┘
                 ↓
           Planning Engine
                 ↓
          Action Proposal
                 ↓
          Human Approval
                 ↓
       Freshness Validation
                 ↓
        Command Structuring
                 ↓
      Deterministic Safety
                 ↓
             Actuation
                 ↓
            ThingsBoard
```

The main design principle is the separation between **AI reasoning** and **physical execution**.

The LLM can interpret requests, reason about building conditions and select capabilities, but actuator commands remain protected by deterministic application logic.

## Workflow

In Workflow mode, requests are routed through an explicit LangGraph structure.

For example:

```text
"What is the comfort in the kitchen?"
                  ↓
              Supervisor
                  ↓
            Comfort Engine
                  ↓
          Sensor Resolution
                  ↓
        ThingsBoard Telemetry
                  ↓
         Comfort Assessment
                  ↓
             Final Answer
```

The software determines the sequence of operations.

## Full ReAct

In Full ReAct mode, the model is provided with tools and dynamically decides which ones to use.

The general interaction is:

```text
Reason
  ↓
Tool Call
  ↓
Observation
  ↓
Reason
  ↓
Final Answer
```

Both architectures use the same BIM, telemetry, comfort, planning and actuation services.

## Human Approval and Actuation

Recommendations that can modify the building follow:

```text
Recommendation
      ↓
Action Proposal
      ↓
Human Approval
      ↓
Freshness Validation
      ↓
Command Structuring
      ↓
Safety Validation
      ↓
Actuation
```

The freshness check verifies that conditions have not changed while the proposal was waiting for a decision.

A direct command such as:

```text
Set the temperature of the kitchen to 22 degrees.
```

does not require another recommendation, but still passes through command structuring and deterministic safety validation before actuation.

---

# Proactive Monitoring

The proactive monitor periodically evaluates the configured rooms.

When discomfort is detected and a compatible actuator exists, the system can create an action proposal.

```text
Room Check
    ↓
Comfort Assessment
    ↓
Uncomfortable?
    ↓
Compatible actuator?
    ↓
Create Proposal
    ↓
Pending Human Decision
```

Only one proactive proposal is handled at a time.

While a proposal is pending, proactive monitoring pauses. It resumes after the proposal is approved, rejected or otherwise resolved.

---

# Observability

The project integrates **Langfuse** for:

* LLM tracing
* tool calls
* execution traces
* latency
* token usage
* proactive executions
* evaluation scores

Langfuse runs independently through:

```text
docker-compose.langfuse.yml
```

with infrastructure configuration stored in:

```text
.env.langfuse
```

---

# Example Queries

BIM:

```text
Which sensors are located in the kitchen?
```

Telemetry:

```text
What is the temperature in the kitchen?
```

Comfort:

```text
What is the comfort in the kitchen?
```

Recommendation:

```text
The kitchen is uncomfortable. What should I do?
```

Actuation:

```text
Set the temperature of the kitchen to 22 degrees.
```

---

# Evaluation

The benchmark dataset is stored in:

```text
benchmarks/core_evaluation_v2.json
```

Workflow example:

```powershell
python -m agentic_bim_iot.benchmark_main `
  --suite benchmarks/core_evaluation_v2.json `
  --orchestration workflow `
  --mode cold `
  --repeat 5 `
  --evaluator deepeval `
  --evaluator ragas `
  --publish-langfuse-scores
```

Full ReAct:

```powershell
python -m agentic_bim_iot.benchmark_main `
  --suite benchmarks/core_evaluation_v2.json `
  --orchestration full_react `
  --mode cold `
  --repeat 5 `
  --evaluator deepeval `
  --evaluator ragas `
  --publish-langfuse-scores
```

The evaluation includes metrics such as:

* task success
* answer correctness
* answer relevancy
* faithfulness
* safety
* latency
* token usage
* LLM calls
* tool calls

Results are stored in:

```text
benchmarks_result/
```

---

# Main Technologies

| Technology     | Purpose                     |
| -------------- | --------------------------- |
| Python 3.12    | Main application            |
| LangGraph      | Workflow orchestration      |
| LangChain      | LLM and tool abstractions   |
| GraphDB        | BIM and semantic data       |
| RDFLib         | RDF processing              |
| Neo4j          | Graph representation        |
| ThingsBoard    | IoT telemetry and actuation |
| MCP            | ThingsBoard integration     |
| Redis          | Optional BIM cache          |
| SQLite         | Application persistence     |
| Streamlit      | Web interface               |
| Langfuse       | Observability               |
| DeepEval       | Evaluation                  |
| RAGAS          | Faithfulness evaluation     |
| Docker Compose | Infrastructure              |

---

# Project Scope

This repository is a research prototype developed for a Master's thesis.

It is not intended to be a production Building Management System.

The main objective is to investigate the differences between an explicit workflow and a more autonomous ReAct agent when operating on real time Smart Building information and actuator capabilities.
