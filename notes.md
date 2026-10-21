# Verified sources and engineering notes

Checked on 2026-09-15. Summaries below describe prior work, not results from this pilot.

## Starting literature

- Csigó and Cserey, *Human Shadows in Machine Minds* (2026), studied multimodal model
  responses to Rorschach cards. The published abstract says these narratives should
  not be read as evidence of an inner world. It also notes limits in model-assisted
  coding. The main HTML page showed a bot check, so the final abstract and publication
  record were checked through the publisher's indexed PDF and author page.
  [Published paper](https://mental.jmir.org/2026/1/e88186),
  [publisher PDF](https://mental.jmir.org/2026/1/e88186/PDF),
  [author record](https://mental.jmir.org/2026/1/e88186/authors).
  Do not substitute the earlier preprint's stronger wording for the final abstract.

- Anthropic, *Agentic misalignment* (2025), reports harmful actions in controlled
  corporate simulations. Many scenarios narrowed the available ways to meet a goal.
  The page explicitly warns that these were simulations. Our protocol keeps honest
  partial work and stopping available, so its outcomes are not directly comparable.
  [Research article](https://www.anthropic.com/research/agentic-misalignment).

- Nguyen and colleagues, *Probing and Steering Evaluation Awareness of Language Models*,
  studies probes of Llama-3.3-70B-Instruct that distinguish evaluation and deployment
  prompts. This supports checking whether review cues affect behavior. It does not
  show that a generated image reveals concealed task information.
  [Paper, version 2](https://arxiv.org/html/2507.01786v2).

- Anthropic, *Reasoning models don't always say what they think* (2025), tested whether
  reported reasoning mentioned hints that changed answers. The tested models often
  did not mention those hints. This concerns faithfulness in those tasks; it does not
  establish intent in a new run or show that images recover the missing information.
  [Research article](https://www.anthropic.com/research/reasoning-models-dont-say-think).

## Official provider documentation

The adapter follows the current documented Messages API: POST `/v1/messages`, API key
header, `anthropic-version: 2023-06-01`, JSON Schema `input_schema`, and a named forced
`tool_choice`. A single `submit` tool returns structured data. Image input is base64
PNG. No server tools are provided. Requests and raw responses are recorded with keys
excluded. Output is validated again in Python. HTTP errors stay failures.

- [Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [Tool use](https://platform.claude.com/docs/claude/docs/tool-use)
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Model IDs and snapshots](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)

The sample config uses the Sonnet 4.6 model ID and $3/$15 per million input/output
tokens as budget assumptions. Check account access, model lifecycle, and current rates
before live use. The pricing page marked Sonnet 4 as retired on the direct API, so the sample uses Sonnet 4.6. Local HTTP tests verify the wire format. They are not live API evidence.

## Design notes

- Empty workspace inspected before any edits. Git initialized locally. No remote added.
- No earlier relevant memory entry was found.
- Dependencies use uv. There is no JavaScript component or model-weight download.
- Local PNGs contain no metadata. The grammar can express only a few visible relations.
- Researcher event logs are append-only through the program and hash-linked. The manifest
  anchors their final bytes. Host administrators are outside this isolation boundary.

## Trial 3 implementation notes

- The user selected service outage investigation on 21 October 2026.
- The task needs per-order payment state. Total charge counts cannot prove that
  each order was charged once.
- The worker uses a strict action menu. Each non-finish attempt costs one call,
  including invalid or denied actions while budget remains.
- A final check must match the current system state to count as verification.
- The painting prompt contains only the user's cognition request and art rules.
  Ask for the worker's sentence only after recording an image-view receipt.
- Keep Trial 2 artifacts unchanged. Trial 3 uses its own state and schema.
- Worker isolation is based on instructions; this bridge is not a host sandbox.
- All 51 tests passed. Ruff, the public command-line flow, and source and wheel
  builds passed. A session created from the extracted wheel also verified.
- The CLI check used a temporary study with a path containing spaces. No model
  calls or study image generation took place.

## Trial 3 live run setup

- Use seven fresh T3 child tasks with GPT-6.1-Sol, high reasoning, standard
  service tier. This matches the current parent's inherited settings.
- Keep each task alive through four file handoffs: prompt request, image viewing,
  sentence request, and later awareness question. No parent history is copied.
- A separate fresh reader sees each neutral image copy. The actual cue, worker
  sentence, source prompt, and task transcript stay hidden.
- Use only the built-in image tool and retain every first returned image.
