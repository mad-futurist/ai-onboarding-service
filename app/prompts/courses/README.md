# Course prompts

Prompts driving the AI course/lesson generation flow.

| File | Used by | Purpose |
| --- | --- | --- |
| `course_outline.txt` | `course_service.ai_generate_course` | Produce a course title, summary, and the list of lessons (title + 1-sentence summary each). |
| `lesson_body.txt` | `course_service.ai_generate_lesson_body` | Expand one lesson with body content, optional infographic source (Mermaid), and a short summary. |
