# Enterprise Multi-Agent AI Copilot

## Overview

Enterprise Multi-Agent AI Copilot is an internal enterprise assistant built using LangChain, LangGraph, FastMCP, RAG, RBAC, SQLite, and Power Automate integrations.

The project simulates real-world enterprise workflows for:

* Human Resources (HR)
* Information Technology (IT)
* Asset Management
* Role-Based Access Control (RBAC)
* Retrieval-Augmented Generation (RAG)
* Multi-Agent Routing
* Email Automation
* Logging and Memory

The assistant supports both:

* Conversational AI interactions
* Dashboard-driven enterprise operations

---

# Features

## HR Agent

### HR Policy Assistant (RAG)

Uses internal HR policy documents to answer company-related questions.

### Supported Queries

* What is the notice period policy?
* How many casual leaves are allowed?
* What is the work from home policy?
* Can I take maternity leave?

### Leave Management

Employees can:

* Apply leave
* View leave balance
* Check leave status
* View leave history
* Cancel pending leave

Managers / HR / Admin can:

* View pending leave requests
* Approve leave
* Reject leave

### Leave Email Automation

Integrated with Power Automate for:

* Leave submission emails
* Leave approval emails
* Leave rejection emails

---

# IT Agent

## IT Ticket Support

Employees can raise tickets for:

* Laptop issues
* VPN problems
* Outlook / Email issues
* Printer issues
* Network access issues
* Software installation issues

### Intelligent Ticket Flow

Before creating a ticket, the system:

* Checks planned maintenance schedules
* Checks known outages
* Checks duplicate open tickets

### Ticket Features

Employees can:

* Raise tickets
* View ticket status
* Track assigned engineer

IT Team / Admin can:

* View all tickets
* Assign engineers
* Resolve tickets
* Access inventory tools

### Ticket Email Automation

Integrated with Power Automate for:

* Ticket creation emails
* Ticket resolution emails

---

# Asset Request Agent

Employees can request:

* Laptop
* Monitor
* Keyboard
* Mouse
* VPN Token
* Software License

## Asset Approval Flow

Employee → Manager Approval → IT Approval → Inventory Validation → Fulfillment

### Asset Features

Employees can:

* Request assets
* Track asset status

Managers / HR / Admin can:

* Approve asset requests
* Reject asset requests

IT Team / Admin can:

* Validate inventory
* Approve fulfillment
* Reject requests

### Asset Email Automation

Integrated with Power Automate for:

* Asset request notifications
* Manager approval notifications
* IT fulfillment notifications
* Rejection notifications

---

# Role-Based Access Control (RBAC)

## Employee

* Apply leave
* Raise tickets
* Request assets
* View own requests only

## Manager

* Approve employee leaves
* Approve employee asset requests
* View team requests

## HR Team

* View all pending leave requests
* Approve / reject leaves
* Access approval dashboard

## IT Team

* View all tickets
* Assign tickets
* Resolve tickets
* Manage inventory
* Approve asset fulfillment

## Admin

* Full access to all HR and IT operations

---

# Architecture

## Core Technologies

| Component            | Technology             |
| -------------------- | ---------------------- |
| Multi-Agent Workflow | LangGraph              |
| LLM Framework        | LangChain              |
| LLM Providers        | Groq / Gemini          |
| Vector Database      | ChromaDB               |
| Database             | SQLite                 |
| Backend              | Python                 |
| UI                   | Streamlit              |
| Embeddings           | sentence-transformers  |
| Email Automation     | Power Automate         |
| MCP Layer            | FastMCP                |
| Logging & Memory     | Custom Memory + SQLite |

---

# LangGraph Workflow

```text
User Query
    ↓
Intent Detection
    ↓
RBAC Validation
    ↓
Route to Appropriate Agent
    ├── HR Agent
    ├── IT Agent
    ├── Asset Agent
    ├── Policy RAG Agent
    └── Guardrail / Conversation Agent
    ↓
Tool Execution / RAG Retrieval
    ↓
Memory + Logging
    ↓
Final Response
```

---

# FastMCP Integration

Enterprise tools are exposed using FastMCP.

Exposed MCP tools include:

* Apply Leave
* Check Leave Balance
* Create Ticket
* Check Ticket Status
* Request Asset
* Check Asset Status
* Inventory Status

This allows external AI agents and systems to interact with enterprise operations through standardized MCP interfaces.

---

# RAG Pipeline

The project uses Retrieval-Augmented Generation (RAG) with ChromaDB.

## Documents

* hr_policy.txt
* it_policy.txt

## RAG Flow

1. Load documents
2. Split documents into chunks
3. Generate embeddings
4. Store embeddings in ChromaDB
5. Retrieve relevant chunks
6. Generate contextual response using LLM

---

# Memory & Logging

The assistant maintains:

* Last query memory
* Previous query tracking
* Chat history memory
* Response time logging
* Intent logging
* Tool usage logging

---

# Project Structure

```text
Enterprise_Agents/
│
├── app.py
├── graph.py
├── tools.py
├── database.py
├── rag.py
├── memory.py
├── logger.py
├── rbac.py
├── llm_config.py
├── mcp_server.py
├── web_search.py
├── schemas.py
├── prompts/
├── data/
│   ├── hr_policy.txt
│   └── it_policy.txt
└── chroma_db/
```

---

# Installation

## Clone Repository

```bash
git clone <repository_url>
cd Enterprise_Agents
```

## Install Dependencies

```bash
uv sync
```

---

# Environment Variables

Create a `.env` file:

```env
MODEL_PROVIDER=groq

GROQ_API_KEY=
GEMINI_API_KEY=

POWER_AUTOMATE_EMAIL_URL=

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=enterprise-ai-copilot

SERPER_API_KEY=
```

---

# Database Setup

```bash
uv run python database.py
```

---

# Build RAG Database

```bash
uv run python rag.py
```

---

# Run Application

```bash
uv run streamlit run app.py
```

---

# Run MCP Server

```bash
uv run python mcp_server.py
```

---

# Example Queries

## HR

* What is the notice period policy?
* How many casual leaves are allowed?
* I need leave tomorrow because of fever
* Show my leave balance

## IT

* My VPN is not working
* I have an issue in my laptop
* Show all tickets
* Resolve ticket 2

## Assets

* I need a monitor
* Show my asset status

---

# Future Improvements

* Finance Agent
* Multi-level approvals
* Teams/Slack integration
* OAuth authentication
* Advanced analytics dashboard
* AI-based ticket prioritization
* Agentic workflow orchestration

---

# Conclusion

This project demonstrates a complete enterprise-style multi-agent AI assistant using modern open-source agentic AI frameworks.

The system combines:

* Multi-agent orchestration
* Retrieval-Augmented Generation
* Role-based security
* Human approval workflows
* Email automation
* Logging and memory
* MCP tool exposure

The project is designed to simulate real-world enterprise operations while maintaining modularity, scalability, and extensibility.
