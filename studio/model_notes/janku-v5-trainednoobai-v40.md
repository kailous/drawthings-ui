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

## Related Civitai Research

- Query result: [Wai x Janku + NovaMoon-PM ILL XL](https://civitai.com/models/1842036)
- Civitai model id: `1842036`
- Creator: `Patuwa`
- Model type: `Checkpoint`
- Base family: `Illustrious`
- Relationship: related Janku/Wai/NoobAI/Illustrious family result; not confirmed to be the exact same local file as `janku_v5_nsfw_trainednoobai_v40_f16.ckpt`.
- Public stats observed: 3,852 downloads, 245 thumbs up, 1 thumbs down, 6 comments.
- Civitai generation support: not available on-site for this model.

### Civitai Version Notes

| Version | Version ID | File | Size | Safety scan | AutoV2 | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| vZero | `2466763` | `waiXJankuNovamoonPM_vzero.safetensors` | ~6.5 GB | pickle success, virus success | `8C25C1D84C` | More normal anime look; less glossy and less 2.5D/3D. |
| Reforged | `2464944` | `waiXJankuNovamoonPM_reforged.safetensors` | ~6.5 GB | pickle success, virus success | `A3FC9A61D9` | Better backgrounds and anatomy; more 2.5D/3D. |
| v(not)Final | `2365623` | `waiXJankuNovamoonPM_vNotFinal.safetensors` | ~6.5 GB | pickle success, virus success | `B15CAAB480` | Slightly improved backgrounds, hands, and anatomy. |
| v5.5 | `2586644` | `waiXJankuNovamoonPM_v55.safetensors` | ~6.5 GB | pickle success, virus success | `31A17F2B75` | Older 2.5D variant. |
| v3.0 | `2263300` | `waiXJankuNovamoonPM_v30.safetensors` | ~6.9 GB | pickle success, virus success | `1EA1922553` | Earlier public version. |
| v2.0 | `2117351` | `waiXJankuNovamoonPM_v20.safetensors` | ~6.9 GB | pickle success, virus success | `375B450306` | Earlier public version. |
| v1.0 | `2084577` | `waiXJankuNovamoonPM_v10.safetensors` | ~6.9 GB | pickle success, virus success | `252499BD31` | Initial public version. |

### Civitai Parameter Hints

- Sampler/scheduler: Euler a with Normal, Simple, or SGM Uniform is the general recommendation from the model page.
- Sharper output: Euler Beta or DPM++ 2M/3M/4M SDE Karras can increase sharpness and detail.
- Steps: start around 10 for Euler/Euler a and 16 for DPM; cap around 35 before testing for diminishing returns.
- CFG: Civitai author recommends starting from `2.5+`; current Draw Things local setting is `7.5`, so compare lower CFG values before assuming the local default is optimal.
- Resolution: SDXL-style resolutions are expected; author commonly uses tall 1024/1152 x 1536 style sizes. Current local `768x1152` is a lighter vertical preset.
- Base quality tags from Civitai: `best quality, masterpiece`.
- Basic negative quality tags from Civitai: `hands, extra digits, worst quality, bad quality`.

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

- 2026-05-12: Added related Civitai research for Wai x Janku + NovaMoon-PM ILL XL.
- 2026-05-12: Initial note created from Draw Things current settings probe.
