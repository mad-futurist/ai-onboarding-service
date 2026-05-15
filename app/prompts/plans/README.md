# Plan prompts

This folder hosts prompt templates that drive the AI plan generation flow.

| File | Used by | Purpose |
| --- | --- | --- |
| `week_regeneration.txt` | `ai_plan_partial_service.regenerate_week` | Rewrite one week's summary and tasks, honoring a `protected_fields` list per task. |
| `task_regeneration.txt` | `ai_plan_partial_service.regenerate_task` | Rewrite a single task, honoring protected fields. |
| `task_field_suggest.txt` | `ai_plan_partial_service.ai_suggest_task_field` | Generate a single field (`acceptance_criteria` / `description` / `examples` / `links`) for one task. |
| `task_generate.txt` | `ai_plan_partial_service.ai_generate_single_task` | Draft one brand-new task from a short hint, with optional week/sprint context. |

The legacy full-plan prompt remains at `app/prompts/plan_generation.txt` and is loaded by `ai_plan_service.load_prompt_template()` to preserve the existing flow.
