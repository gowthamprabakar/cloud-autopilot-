---
name: Vibe-Coding Support Tools Reference
description: 7 GitHub repos cloned to vibe-tools/ for use as reference/tooling during Cloud Posture Copilot development
type: reference
---

# Vibe-Coding Support Repos

Location: `/Users/prabakarannagarajan/Desktop/cloud copilot /vibe-tools/`

| Repo | Local Dir | Purpose | Relevance |
|------|-----------|---------|-----------|
| msitarzewski/agency-agents | `agency-agents/` | Complete AI agency framework (frontend wizards, Reddit community agents etc.) | Multi-agent orchestration patterns for AI assist layer |
| 666ghj/MiroFish | `MiroFish/` | Simple Universal Swarm Intelligence Engine — predicts anything | Swarm/ensemble intelligence patterns |
| promptfoo/promptfoo | `promptfoo/` | Test prompts, agents, RAGs. Red teaming/pentesting/vuln scanning | **HIGH PRIORITY** — use for prompt registry testing, AI output validation, eval framework |
| pbakaus/impeccable | `impeccable/` | Design language that makes AI harnesses better at design | UI/component design patterns for AI integration |
| volcengine/OpenViking | `OpenViking/` | Open-source context database for AI Agents | Context management patterns for bounded context builders |
| p-e-w/heretic | `heretic/` | Fully automatic censorship removal for LLMs | ⚠️ Jailbreak/bypass tool — study for understanding AI safety boundaries only |
| karpathy/nanochat | `nanochat/` | Best ChatGPT $100 can buy — minimal implementation | Reference for minimal, clean AI chat implementation patterns |

## Priority Usage
- **promptfoo**: Use for building the AI Eval Framework defined in SSOT
- **OpenViking**: Reference for context database design in AI bounded context builders
- **agency-agents**: Reference for multi-agent patterns in AI assist layer
- **nanochat**: Reference for clean, minimal AI integration
- **impeccable**: Reference for AI-aware design system patterns
