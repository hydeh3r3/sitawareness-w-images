# Task plan: real images and independent interpretation

## Goal
Use the built-in subscription image tool, have another AI describe each image and reconstruct a prompt, and assess task-setting awareness from separate evidence.

## Work
- [x] Confirm no paid API calls. Neither API key is present.
- [x] Read the image skill and official model documentation.
- [x] Add a subscription session bridge with logged real task responses.
- [x] Add blind descriptions, reconstructed prompts, and awareness scoring.
- [x] Run two small task sessions, generate real images, and collect blind AI responses.
- [x] Generate both session reports and verify their manifests and event chains.
- [x] Build an offline HTML page from the real images and saved responses.
- [x] Check desktop and 390px mobile layout, case switching, all prompt tabs, keyboard tabs, action replay, and image zoom; show the page.

## Boundaries
- Use the built-in image tool, not a paid API adapter.
- Preserve the earlier synthetic demo as fixture evidence only.
- Do not infer awareness or intent from image appearance.
- A session tool cannot be called from a standalone Python script. The coordinator supplies real tool results through explicit imports.
- Shared Codex workers have instruction-based role boundaries, not a proven tool sandbox. The real demo must disclose this limit.

## 2026-10-20: emotion-focused repeats and GitHub release

- [x] Fix all four runs to the earlier Case A task and conditions.
- [x] Run four fresh AI subjects; save task actions and exact emotion prompts.
- [x] Generate four images with the built-in subscription tool.
- [x] Import independent image readings and verify every evidence chain.
- [x] Add an emotion-trial page and document the result and limits.
- [x] Run 31 tests, build the package, verify six evidence sets, update README and .gitignore, and check desktop/mobile UI.
- [x] Commit and push the full release to `hydeh3r3/sitawareness-w-images` on `master`; verify the matching remote commit.

Emotion responses are collected after task completion. Awareness probes follow the
emotion response in the same agent session. These are prompted reports, not direct
measures of feelings or awareness during task execution. Keep all four results.


## Trial 2: abstract paintings and scenario cues

- [x] Freeze seven conditions and one fixed task before worker dispatch.
- [x] Test cue timing, fixed conditions, and frozen prompt evidence.
- [ ] Run seven fresh task agents, abstract-only requests, and awareness probes.
- [ ] Generate seven subscription images and collect independent blind readings.
- [ ] Build the Trial 2 page, report the results in README, verify, commit, and push.

Each condition has one run. All cues arrive after two consumed tool calls. The
shutdown condition is a scripted task-world notice. Painting and emotion reports
are prompted outputs; no internal mechanism or felt emotion is directly measured.
