# research_helper

A lightweight toolkit to help you move from idea to insight faster. research_helper provides a simple UI on top of large language models plus a small set of carefully designed algorithms to assist with common research workflows (brainstorming, structuring, synthesis, and critique).

- UI entry point: [ui.py](https://github.com/peterdunson/research_helper/blob/main/ui.py)
- LLM wrapper and orchestration: [llm_wrapper.py](https://github.com/peterdunson/research_helper/blob/main/llm_wrapper.py)
- Environment and dependencies: [requirements.txt](https://github.com/peterdunson/research_helper/blob/main/requirements.txt), [Dockerfile](https://github.com/peterdunson/research_helper/blob/main/Dockerfile)

## Key Features

- Minimal, fast UI to run research workflows locally
- Extensible LLM wrapper for prompt/parameter control and reproducibility
- Three built-in algorithms for research assistance (see below)
- Simple testing scaffolding in [tests/](https://github.com/peterdunson/research_helper/tree/main/tests)

## The Three Algorithms

research_helper ships with three complementary algorithms exposed via the UI. They are designed to be simple, interpretable building blocks you can mix and match:

1) Idea-to-Outline (Decompose and Structure)
   - Goal: Turn an initial topic or question into a structured, sectioned outline with objectives, variables, and candidate methods.
   - How it works: Uses guided prompting in stages (problem statement → sub-questions → section plan → deliverables). Emphasizes clarity and specificity over verbosity.
   - Typical inputs: Research topic, constraints, preferred methodology.
   - Typical outputs: Hierarchical outline with section goals, key citations to find, and a checklist of next steps.

2) Evidence Synthesizer (Summarize and Compare)
   - Goal: Given notes, abstracts, or excerpts, synthesize key findings, contrasts, and gaps.
   - How it works: Normalizes inputs to a common schema, produces per-item structured summaries, then aggregates with comparison tables and gap statements.
   - Typical inputs: Bullet notes, abstracts, selected paragraphs.
   - Typical outputs: Consolidated summary, contrastive matrix, prioritized open questions.

3) Critique-and-Revise (Reviewer-in-the-Loop)
   - Goal: Provide actionable feedback on a draft section or plan, then generate a revised version.
   - How it works: Two-pass loop—first a constrained critique (clarity, evidence, methods, limitations), then a targeted rewrite that addresses each critique point.
   - Typical inputs: Draft paragraphs, outlines, or method plans.
   - Typical outputs: Reviewer notes plus a revised draft that explicitly resolves each point.

Notes:
- The UI lets you switch among algorithms and adjust model parameters.
- The exact steps and prompts are implemented in [llm_wrapper.py](https://github.com/peterdunson/research_helper/blob/main/llm_wrapper.py). Use that file to customize prompts, temperature, max tokens, and chain logic.

## Quick Start

Prerequisites
- Python 3.10+ recommended
- An API key for your chosen LLM provider (e.g., set OPENAI_API_KEY as an environment variable if using OpenAI)

Install
```bash
# from the repo root
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run the UI
```bash
python ui.py
```

Environment variables (examples)
```bash
export OPENAI_API_KEY=sk-...
# Optional: model selection and defaults
export MODEL_NAME=gpt-4o-mini
export TEMPERATURE=0.2
```

## Docker

A minimal Dockerfile is included for containerized runs.

Build and run
```bash
docker build -t research_helper .
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY -p 7860:7860 research_helper
```

## Project Structure

```text
.
├─ README.md                # You are here
├─ requirements.txt         # Python dependencies
├─ Dockerfile               # Container image definition
├─ ui.py                    # App entry point / UI
├─ llm_wrapper.py           # LLM orchestration and algorithm logic
├─ app/                     # UI or app-specific assets/modules
├─ tests/                   # Basic tests and examples
└─ __pycache__/             # Python cache (generated)
```

Browse key files:
- [ui.py](https://github.com/peterdunson/research_helper/blob/main/ui.py)
- [llm_wrapper.py](https://github.com/peterdunson/research_helper/blob/main/llm_wrapper.py)
- [requirements.txt](https://github.com/peterdunson/research_helper/blob/main/requirements.txt)
- [Dockerfile](https://github.com/peterdunson/research_helper/blob/main/Dockerfile)
- [app/](https://github.com/peterdunson/research_helper/tree/main/app)
- [tests/](https://github.com/peterdunson/research_helper/tree/main/tests)

## Usage Patterns

- Rapid outlining: Start with Algorithm 1 to turn a topic into a concrete plan.
- Literature notes → synthesis: Feed excerpts into Algorithm 2 to get a contrastive summary and gaps.
- Tighten a draft: Use Algorithm 3 to get reviewer-style feedback and an improved revision.

## Testing

Run the tests (if any are present in [tests/](https://github.com/peterdunson/research_helper/tree/main/tests)):
```bash
pytest -q
```

## Extending

- Add new algorithms by creating a new function or class in [llm_wrapper.py](https://github.com/peterdunson/research_helper/blob/main/llm_wrapper.py) and wiring it into [ui.py](https://github.com/peterdunson/research_helper/blob/main/ui.py).
- Expose parameters (model, temperature, steps) through the UI for quick experimentation.
- Keep prompts modular to enable A/B testing across tasks.

## Disclaimer

This tool assists with research workflows but does not replace domain expertise. Always verify generated claims and references.

