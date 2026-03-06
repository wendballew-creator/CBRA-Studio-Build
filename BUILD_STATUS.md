# CBRA API Build Status

## Current branch
`feat/staged-diffractive-map`

## Build state
Stabilized runtime build after:
- compression enforcement audit
- drift event persistence alignment
- final schema hygiene pass

## Live runtime files
- `main.py`
- `cbra_engine.py`
- `cbra/models.py`
- `cbra/store.py`
- `cbra/compression.py`

## Verified behaviors
- `/thread/{thread_id}` auto-creates a thread and returns thread payload
- `/chat/{thread_id}` appends messages, persists loop cycles, and emits drift events when drift is detected
- `selected_elements` is enforced and mirrored
- `LoopCycle.selected_elements` persists
- `LoopCycle.notes` persists
- `FieldArtifact.selected_elements` persists
- `FieldArtifact.notes` persists
- `DriftEvent` aligns with `LoopCycle.notes`
- duplicate drift events are suppressed only when:
  - `kind`
  - `detected_at_stage`
  - `reintegration_target`
  - `reintegration_stage`
  all match the most recent drift event exactly

## Current data model guarantees

### FieldArtifact
Persists:
- `field_signature`
- `noticing_register`
- `relational_map`
- `diffractive_map`
- `relevance_gradient`
- `selected_elements`
- `notes`

### LoopCycle
Persists:
- `field_id`
- `field_signature`
- `noticing_register`
- `relational_map`
- `diffractive_map`
- `relevance_gradient`
- `selected_elements`
- `notes`
- `articulation_output`
- `action_vector`
- `drift_detected`
- `reintegration_stage`

### DriftEvent
Persists:
- `kind`
- `severity`
- `reintegration_target`
- `detected_at_stage`
- `reintegration_stage`
- `notes`

## Known limitations
- Store is in-memory only; thread data resets when uvicorn restarts
- Reintegration stage may vary across identical prompts because model output varies
- File route schema block was cleaned, but a dedicated live uploaded-file test should still be run later
- Local backup files were deleted and are ignored by `.gitignore`

## Minimum verification commands

### Compile
```bash
python -m compileall -q .
curl -sS "http://127.0.0.1:8000/thread/build-status-check" | python -m json.tool
curl -sS -X POST "http://127.0.0.1:8000/chat/build-status-check" \
  -H "Content-Type: application/json" \
  -d '{"user_text":"build status verification turn","mode":"production"}' \
  | python -m json.tool
curl -sS "http://127.0.0.1:8000/thread/build-status-check" | python -m json.tool
