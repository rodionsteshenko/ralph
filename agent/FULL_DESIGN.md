Chat Agent Platform — Design Canvas

1. Product intent (one-liner)

A chat agent that remembers, retrieves, learns about the user over time, and acts deliberately via tools, while remaining inspectable, correctable, and user-controlled.

⸻

2. Core system pillars

Pillar A — Conversation & Context
	•	Bounded recent chat window
	•	Time augmentation (current time, timezone)
	•	Tool outputs included in history
	•	Session-level style overrides

⸻

Pillar B — Knowledge & Memory

Four distinct memory types (non-negotiable separation)
	1.	Chat history
	•	Verbatim turns
	•	Short-term coherence only
	2.	RAG Knowledge Store
	•	Embedded messages
	•	URLs, clipboard, RSS, files
	•	Searchable by similarity, tags, filters
	3.	Compact Conversation Memory
	•	Periodic summaries
	•	Decisions, open threads, entities
	•	Injected for long-running continuity
	4.	User Profile (structured facts)
	•	Identity, interests, preferences, relationships
	•	Confidence-based, confirmable, decaying

⸻

Pillar C — Agent Behavior & Personality
	•	Persistent AgentStyleProfile
	•	User-editable personality knobs
	•	Presets + freeform tuning
	•	Background inference with optional confirmation

⸻

Pillar D — Agent Reasoning Loop
	•	Decide → act → observe → repeat
	•	“Done / not done” explicit state
	•	Tool calls streamed to UI
	•	Hard caps on steps and time

⸻

Pillar E — Ingestion Pipelines
	•	Chat ingestion
	•	Clipboard ingestion
	•	URL ingestion (auto-fetch)
	•	RSS ingestion (polling)
	•	(Future) Files, PDFs, directories, spreadsheets

⸻

Pillar F — Search & External Knowledge
	•	Internal vector search (primary)
	•	Keyword search
	•	Web search (Tavily / Google) as last resort
	•	Explicit storage decision for external results

⸻

Pillar G — Governance & Trust
	•	Explainability (“why do you know this?”)
	•	Memory correction & deletion
	•	Retention & decay
	•	Sensitive-data guardrails
	•	User-visible profile & style controls

⸻

3. Feature inventory (flattened)

Chat & Prompting
	•	Time injection
	•	Configurable recent-window size
	•	Tool messages in chat history

Retrieval (RAG)
	•	Vector search (top-N)
	•	Tag filtering
	•	Source-type filtering
	•	Recency weighting
	•	Hybrid search (later)

Memory ingestion
	•	Store chat turns
	•	Clipboard text ingestion
	•	URL scrape + extract
	•	Deduplication
	•	Auto-tagging

Compact memory
	•	Periodic conversation summarization
	•	Decision extraction
	•	Open thread tracking

User knowledge
	•	Structured UserProfile
	•	Background fact extraction
	•	Confidence & decay
	•	Confirmation workflow
	•	Conflict handling

Agent personality
	•	Style profile store
	•	User commands (“use fewer emojis”)
	•	Background style inference
	•	Presets
	•	Session overrides

Agent loop
	•	Tool-calling LLM
	•	Step limits
	•	Tool event logging
	•	UI trace

Search
	•	Internal vector search tool
	•	Keyword search tool
	•	Web search tool (Tavily / Google)
	•	Optional persistence of results

Governance
	•	View/edit memory UI
	•	Forget / pin memory
	•	Source attribution
	•	Sensitive-fact rules

⸻

4. Phased implementation plan

Phase 0 — Foundations (must exist before “smart”)

Goal: Reliable chat + storage + retrieval
	•	Chat API + orchestrator
	•	Message storage
	•	Vector DB + embeddings
	•	Always-on RAG retrieval
	•	Time augmentation
	•	Simple agent loop (single tool call max)
	•	Basic UI showing tool calls

Exit criteria
	•	Chat works end-to-end
	•	Retrieval improves answers
	•	No silent failures

⸻

Phase 1 — Knowledge ingestion

Goal: The system can learn from user inputs beyond chat
	•	URL auto-ingestion
	•	Clipboard ingestion (text only)
	•	KnowledgeItem abstraction
	•	Deduplication
	•	Auto-tagging (lightweight)
	•	Vector + metadata search

Exit criteria
	•	Pasted URLs are searchable later
	•	Clipboard content shows up in RAG
	•	Tags filter retrieval

⸻

Phase 2 — Compact memory

Goal: Long conversations stay coherent
	•	Conversation summary generator
	•	Summary storage + retrieval
	•	Prompt injection logic
	•	Manual “summarize this” action

Exit criteria
	•	Long chats do not degrade
	•	Summaries are inspectable and traceable

⸻

Phase 3 — User profile (structured memory)

Goal: The agent knows who the user is, safely
	•	UserProfile schema
	•	Background fact extraction agent
	•	Confidence scoring + decay
	•	Confirmation UX
	•	Profile injection into system prompt

Exit criteria
	•	User can view/edit profile
	•	No silent incorrect assumptions
	•	Facts influence answers correctly

⸻

Phase 4 — Agent personality & style

Goal: The agent adapts its behavior over time
	•	AgentStyleProfile
	•	Explicit user commands
	•	Background style inference
	•	Presets + session overrides
	•	Style injection into prompt

Exit criteria
	•	User can tune behavior
	•	Changes persist and are explainable

⸻

Phase 5 — Search & research agent

Goal: Controlled external knowledge acquisition
	•	Web search tool (Tavily / Google)
	•	Storage decision logic
	•	Citation handling
	•	Multi-step research loop

Exit criteria
	•	Agent searches only when needed
	•	Search results are traceable
	•	Stored only when valuable

⸻

Phase 6 — Governance & trust hardening

Goal: User trust and long-term stability
	•	“Why do you know this?” queries
	•	Memory pinning / forgetting
	•	Sensitive-fact protections
	•	Retention policies
	•	Audit & tool logs

Exit criteria
	•	User trusts the system
	•	Memory is controllable
	•	No opaque behavior

⸻

5. Architectural invariants (rules you should not break)
	•	UserProfile ≠ RAG memory
	•	Style preferences ≠ user identity
	•	No silent long-term memory writes
	•	All summaries trace back to sources
	•	Web search is never default
	•	Everything stored must be explainable

⸻

6. What this canvas gives you
	•	Clear separation of concerns
	•	Natural staging for implementation
	•	Avoids memory collapse and prompt bloat
	•	Supports future agents, tools, and modalities without rewrites

If you want, next logical steps would be either:
	1.	Turning Phase 0–1 into an implementation checklist with schemas and APIs, or
	2.	Writing a single “Profiles & Memory Spec” that formalizes UserProfile, StyleProfile, and Compact Memory together.