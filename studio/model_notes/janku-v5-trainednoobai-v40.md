# Janku V5 TrainedNoobAI v40

## Identity

- Provider/source: local Draw Things installation
- Base architecture: unknown
- File name: `janku_v5_nsfw_trainednoobai_v40_f16.ckpt`
- Version: v40, inferred from file name
- First tested: 2026-05-12
- Draw Things import status: installed locally

## Best Use Cases

- Anime-style portrait and character illustration.
- Vertical character compositions.
- Soft lighting and high-detail illustration workflows.

## Weak Spots

- Needs local testing notes before publishing strong conclusions.
- Current API probe only confirms the active model, not the full installed model list.

## Recommended Parameters

| Setting | Recommendation | Notes |
| --- | --- | --- |
| Width x Height | `768x1152` | Current Draw Things setting observed via API. |
| Steps | `40` | Current Draw Things setting observed via API. |
| Sampler | `Euler A Substep` | Current Draw Things setting observed via API. |
| CFG / Guidance | `7.5` | Current Draw Things `guidance_scale`. |
| Clip Skip | `2` | Current Draw Things setting observed via API. |
| Refiner | none observed | `refiner_model` returned `null`. |
| LoRA/Control compatibility | no LoRA active | Current `loras` list was empty. |

## Prompting Notes

- Keep model notes focused on reusable style and parameter behavior.
- Avoid recording private prompt text in this public note.
- Add observations only after comparing multiple generated outputs.

## Negative Prompt Notes

- Use normal quality-control negatives for anatomy, hands, blur, text, and watermarks.
- Keep private or case-specific negative prompts in ignored local notes.

## Performance Notes

- Device: not recorded
- Peak memory: not recorded
- Typical generation time: not recorded
- Stability: not recorded

## Import Notes

- Already available in the active Draw Things installation.
- API probe source: `/sdapi/v1/options`

## Changelog

- 2026-05-12: Initial note created from Draw Things current settings probe.
