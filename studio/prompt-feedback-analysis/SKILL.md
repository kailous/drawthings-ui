---
name: prompt-feedback-analysis
description: Use this skill when analyzing Draw Things prompt feedback saved in this project, especially studio/good_cases/ and studio/bad_cases/ rating archives, to identify prompt patterns and generate practical guidance for future prompt editing.
---

# Prompt Feedback Analysis

Use this skill to turn rated image-generation history into prompt-editing guidance.

## Data Sources

Read project-local rating archives:

- `studio/good_cases/*/feedback.json` and `studio/good_cases/*/prompt.json`
- `studio/bad_cases/*/feedback.json` and `studio/bad_cases/*/prompt.json`
- Existing hand-written case notes such as `studio/good_cases/*_analysis.md` and `studio/bad_cases/README.md` when relevant
- `studio/KNOWLEDGE_BASE.md` only when the user asks for deeper prompt strategy or pattern synthesis

Each rating archive should contain:

- `result.*`: copied image
- `prompt.json`: generation payload parsed from Draw Things metadata
- `feedback.json`: rating, user note, source image, metadata, created_at

## Workflow

1. Inventory rated cases.
   - Count good and bad examples.
   - Prefer newer `feedback.json` archives over older loose case files.
   - Note gaps if a folder lacks `prompt.json` or `feedback.json`.

2. Extract prompt signals.
   - Compare positive and negative prompts between good and bad cases.
   - Track repeated phrases, weighted phrases, sampler/steps/cfg/seed metadata, and image dimensions.
   - Treat user notes as higher priority than filename text.

3. Separate guidance by actionability.
   - **Keep**: prompt patterns that repeatedly correlate with good feedback.
   - **Avoid**: terms, weights, or structures that correlate with bad feedback.
   - **Revise**: patterns that are useful but need lower weight, more concrete wording, or better negative prompts.
   - **Experiment**: uncertain hypotheses that need more rated examples.

4. Generate editor-ready guidance.
   - Be concrete: quote short prompt fragments, exact weights, and replacement phrasing.
   - Prefer small edits over rewriting entire prompts.
   - Include an example “next prompt patch” when useful.
   - If evidence is weak, say so and avoid overstating conclusions.

## Useful Script

Run the bundled analyzer from the repository root:

```bash
python3 studio/prompt-feedback-analysis/scripts/analyze_feedback.py
```

It prints a Markdown report summarizing rated cases, common terms, parameter ranges, and user notes.
Use the script output as raw evidence, then apply judgment to write final guidance.

## Output Shape

For a normal analysis request, respond with:

```markdown
**样本概况**
...

**保留**
...

**避免**
...

**下一轮提示词编辑建议**
...

**还需要补充的数据**
...
```

Keep the guidance practical and tied to the saved cases. Do not invent visual conclusions from prompts alone unless the actual images were inspected.
