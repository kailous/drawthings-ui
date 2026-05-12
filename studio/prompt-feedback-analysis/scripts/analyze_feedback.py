#!/usr/bin/env python3
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE_DIRS = {
    "good": ROOT / "good_cases",
    "bad": ROOT / "bad_cases",
}


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def iter_cases():
    for rating, root in CASE_DIRS.items():
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            feedback = load_json(folder / "feedback.json")
            prompt = load_json(folder / "prompt.json")
            if feedback or prompt:
                yield {
                    "rating": rating,
                    "folder": folder,
                    "feedback": feedback or {},
                    "prompt": prompt or {},
                }


def tokenize_prompt(text):
    if not isinstance(text, str):
        return []
    tokens = []
    for part in re.split(r"[,;\n]+", text):
        token = re.sub(r"\s+", " ", part.strip().lower())
        token = token.strip("()[]{} ")
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def weight_fragments(text):
    if not isinstance(text, str):
        return []
    return re.findall(r"\(([^:()]{3,80}):([0-9.]+)\)", text)


def summarize_params(cases):
    values = defaultdict(list)
    for case in cases:
        prompt = case["prompt"]
        for key in ("steps", "width", "height", "cfg_scale", "clip_skip", "sampler"):
            if key in prompt:
                values[key].append(prompt[key])
    return values


def render_counter(counter, limit=12):
    if not counter:
        return "- 无"
    return "\n".join(f"- `{term}`: {count}" for term, count in counter.most_common(limit))


def main():
    cases = list(iter_cases())
    by_rating = {
        "good": [case for case in cases if case["rating"] == "good"],
        "bad": [case for case in cases if case["rating"] == "bad"],
    }

    counters = {}
    weighted = {}
    notes = {}
    for rating, rating_cases in by_rating.items():
        prompt_terms = Counter()
        negative_terms = Counter()
        weighted_terms = Counter()
        rating_notes = []
        for case in rating_cases:
            prompt = case["prompt"]
            prompt_terms.update(tokenize_prompt(prompt.get("prompt", "")))
            negative_terms.update(tokenize_prompt(prompt.get("negative_prompt", "")))
            weighted_terms.update(f"{frag.strip().lower()}:{weight}" for frag, weight in weight_fragments(prompt.get("prompt", "")))
            note = str(case["feedback"].get("note", "")).strip()
            if note:
                rating_notes.append((case["folder"].name, note))
        counters[(rating, "prompt")] = prompt_terms
        counters[(rating, "negative")] = negative_terms
        weighted[rating] = weighted_terms
        notes[rating] = rating_notes

    print("# Prompt Feedback Analysis")
    print()
    print("## 样本概况")
    print(f"- 好评案例: {len(by_rating['good'])}")
    print(f"- 差评案例: {len(by_rating['bad'])}")
    print()

    for rating, label in (("good", "好评"), ("bad", "差评")):
        print(f"## {label}高频正向片段")
        print(render_counter(counters[(rating, "prompt")]))
        print()
        print(f"## {label}高频反向片段")
        print(render_counter(counters[(rating, "negative")], limit=8))
        print()
        print(f"## {label}高频权重片段")
        print(render_counter(weighted[rating], limit=8))
        print()

    params = summarize_params(cases)
    print("## 参数分布")
    if not params:
        print("- 无")
    else:
        for key, vals in sorted(params.items()):
            counts = Counter(str(v) for v in vals)
            top = ", ".join(f"`{v}` x{n}" for v, n in counts.most_common(6))
            print(f"- `{key}`: {top}")
    print()

    for rating, label in (("good", "好评"), ("bad", "差评")):
        print(f"## {label}用户备注")
        if not notes[rating]:
            print("- 无")
        else:
            for folder, note in notes[rating][:20]:
                print(f"- `{folder}`: {note}")
        print()

    missing = []
    for root_name in ("good_cases", "bad_cases"):
        root = ROOT / root_name
        if root.is_dir():
            for folder in root.iterdir():
                if folder.is_dir() and not ((folder / "feedback.json").exists() and (folder / "prompt.json").exists()):
                    missing.append(f"{root_name}/{folder.name}")
    print("## 数据缺口")
    if missing:
        for item in missing[:30]:
            print(f"- `{item}` 缺少 `feedback.json` 或 `prompt.json`")
    else:
        print("- 暂无明显缺口")


if __name__ == "__main__":
    main()
