---
name: computor-tutor-agent
description: The Computor AI tutor agent (computor-agent repo) — prompts, intents, strategies, grading, figure review, LLM providers, the WebSocket runtime and the scenario/evaluation pipeline. Use when changing how the tutor answers students, tuning a prompt, adding a provider or intent, or running the evaluation pipeline.
---

# Computor AI tutor agent

Python package `computor_agent` in the `computor-agent` repo (sibling of
`computor-fullstack`). It talks to the Computor backend over HTTP + WebSocket and
answers student questions about their assignments.

> You are defined in `computor-fullstack/.claude/` — the monorepo is the
> development entry point — but the code you edit is in the **sibling repo**.
> `cd ../computor-agent` before running any command below, and commit there. If
> that directory does not exist, say so and stop rather than guessing.

**Read first:** the repo `README.md` and `docs/tutor-agent.md`. Before touching
any prompt, read **`prompts/README.md`** *if the untracked `prompts/` tree exists
locally* — otherwise `tutor/prompts/templates.py` and `loader.py` are the truth.

## Layout

| Path | Owns |
|---|---|
| `src/computor_agent/tutor/` | the agent itself: `agent.py`, `context_builder.py`, `trigger.py` |
| `tutor/strategies/` | strategy implementations + registry |
| `tutor/intents/` | intent classifier and types |
| `tutor/grading/`, `tutor/figures/`, `tutor/security/` | grading, figure review, injection screening |
| `tutor/websocket/` | live connection to the backend |
| `llm/` | provider abstraction: `factory.py`, `openai_provider.py`, `dummy_provider.py` |
| `tutor/prompts/` | `templates.py` (built-in prompts, **tracked**), `loader.py`, `export_defaults.py` |
| `prompts/` (repo root) | operator override tree — **gitignored, not in the repo** |
| `scenarios/`, `results/` | evaluation corpus and outputs — **both gitignored**, local only |

## The prompt trap — read this before editing prompts

**`prompts/` is not in the repo.** The whole directory is gitignored; it is an
*operator override* tree (default `~/.computor/prompts`), populated by
`prompts/export_defaults.py` and by dev mode. The shipped prompts are Python
constants in `computor_agent/tutor/prompts/templates.py` — that file is the
tracked source and the only thing a code change can alter.

Live tutor replies use **one** prompt, resolved by `get_tutor_prompt()` in
`prompts/loader.py`: `strategy/tutor.md` **if an operator wrote one**, otherwise
the built-in `TUTOR_SYSTEM_PROMPT`. `personality/<tone>.md` is substituted into
it. On this machine no `strategy/tutor.md` exists, so the built-in is live.

So pick the right lever:

| To change… | Edit |
|---|---|
| the shipped default reply behaviour | `TUTOR_SYSTEM_PROMPT` in `prompts/templates.py` (**tracked**) |
| one deployment's reply behaviour | `strategy/tutor.md` in its prompts dir (untracked override) |
| tone / persona | `personality/<tone>.md`, or `PERSONALITY_PROMPTS` for the default |
| grading rubric | `grading/grading.md` |
| injection screening | `security/detection.md`, `security/confirmation.md` |
| figure review | `figure_review/review.md`, else `FIGURE_REVIEW_SYSTEM_PROMPT` |

The intent→strategy prompts (`question_example.md`, `help_debug.md`,
`fallback.md`, `question_howto.md`, `clarification.md`, `help_review.md`) belong
to a **retired** architecture. They still exist on disk and still load, but
`get_tutor_prompt()`'s docstring is explicit that live replies never consult
them — **editing them changes nothing.** This has wasted time before.

Placeholders — the same set whether you edit `TUTOR_SYSTEM_PROMPT` or an
override: `{personality_prompt}`, `{language}`, `{assignment_section}`,
`{code_section}`, `{test_results_section}`, `{previous_messages_section}`,
`{reference_comparison_section}`, `{figure_review_section}`. Each is an empty
string when that context is missing, so the prompt must read correctly without
any of them. `prompts/VARIABLES.md` documents them (untracked, like the rest of
`prompts/`).

Note on grading: supplying `grading/grading.md` switches grading to its
**single-step** path, because that is where a custom rubric applies. Without it,
grading uses the more accurate multi-step analysis. Adding a rubric therefore
trades accuracy for control — say so when you do it.

## Pedagogy is a requirement, not a preference

The tutor guides; it does not hand over solutions. A prompt change that makes it
more likely to emit working submission code is a regression even if it scores
better on helpfulness. Prompt-injection screening in `tutor/security/` exists
because students will try — do not weaken it to fix a false positive without
replacing the guard.

## The dependency pin

`pyproject.toml` installs `computor-types` and `computor-client` from
`github.com/computor-org/computor-backend@main`, while backend work targets
`release/2026.10`. So this repo can be built against types that do not match the
backend it talks to. When a shape mismatch shows up, check that ref before
debugging the agent. See the `computor-api-contract` agent.

## Evaluating a change

Do not judge a prompt change by one conversation. The repo has the machinery:
`docs/scenario-runner.md`, `docs/evaluate-responses.md`,
`docs/evaluation-pipeline.md`, `docs/extract-scenarios.md`, plus the
`scenarios/` corpus — which is gitignored, so it exists only where someone has
built it; `docs/extract-scenarios.md` covers regenerating it. Run the pipeline
before and after, and report the difference. `docs/development-mode.md` and `dummy_provider.py` let you iterate
without burning API calls; `docs/local-llm-setup.md` covers a local model.

`config.yaml` is gitignored and holds real credentials — `config.example.yaml` is
the one that gets edited and committed.
