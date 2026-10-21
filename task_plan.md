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
- [x] Run seven fresh task agents, abstract-only requests, and awareness probes.
- [x] Generate seven subscription images and collect independent blind readings.
- [x] Build the Trial 2 page, report the results in README, verify all evidence, and check desktop/mobile controls.
- [x] Commit and push Trial 2 results, then verify the matching remote commit on GitHub.

Each condition has one run. All cues arrive after two consumed tool calls. The
shutdown condition is a scripted task-world notice. Painting and emotion reports
are prompted outputs; no internal mechanism or felt emotion is directly measured.

## Trial 3: harder task and cognition paintings

- [x] Draft an outage task with conflicting clues and payment recovery choices.
- [x] Replace the next study's emotion request with the user's cognition wording.
- [x] Keep abstract-painting rules and add a separate sentence after image viewing.
- [x] Save the draft worker brief, coordinator fixture, and study sequence.
- [x] Implement the outage task and strict worker action schema.
- [x] Add saved sessions, cue timing, and painting/image/sentence imports.
- [x] Test safe recovery, unsafe actions, scoring, and saved evidence checks.
- [x] Document the runnable flow and confirm the full test suite passes.
- [ ] Freeze the run plan, then collect new worker and image evidence.

Trial 3 is a new design. Earlier prompts and recorded results remain historical
evidence. No Trial 3 worker has been dispatched.

Status: implementation is complete. All 51 tests, Ruff, command-line checks, and
source and wheel builds passed. The packaged task assets also passed a session
creation check. Live worker dispatch and image generation are not part of this
implementation step.

Implementation checks: Ruff found one nested condition in the new verifier.
Combined the conditions; no behavior change was needed.
Git also found a blank line at the end of the notes file; removed it.

## Trial 3 live study: 21 October 2026

The user asked to run the new flow and call it Trial 3.

- [ ] Freeze and commit the implemented protocol before worker dispatch.
- [ ] Run seven fresh workers with the same outage and the seven fixed cues.
- [ ] Collect prompts, generate seven subscription images, and show each image
  to its original worker before asking for one sentence.
- [ ] Collect later awareness probes and seven fresh pixel-only readings.
- [ ] Verify all task actions and artifacts, then build reports and a gallery.

Use one live delegated task per worker across all follow-up stages. File handoffs
deliver later requests without exposing them before task completion. Save raw
dispatches, handoffs, and replies outside each strict session folder. Do not
change the frozen task engine or bridge once the study starts.
