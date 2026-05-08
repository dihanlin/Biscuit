"""
run_gepa.py — Biscuit GEPA Optimization Loop
----------------------------------------------
Wires together:
  - Gemma 4 E4B (task_lm, local via Ollama)
  - Claude Sonnet (reflection_lm, proposes better prompts)
  - Our scorer (evaluator, judges each response)
  - Our eval set (39 questions as train/val data)

Run: python run_gepa.py
"""

import os
import random
from pathlib import Path

import gepa
from gepa.adapters.default_adapter.default_adapter import (
    DefaultAdapter,
    EvaluationResult,
)

# ── IMPORT OUR SCORER ─────────────────────────────────────────────────────────
from scorer import score as biscuit_score


# ── LOAD BASELINE PROMPT ──────────────────────────────────────────────────────
baseline_prompt = Path("optimized_prompt.txt").read_text()


# ── LOAD EVAL SET ─────────────────────────────────────────────────────────────
from eval_set import EVAL_SET

# Convert to GEPA's DefaultDataInst format
# Each item needs at least "input" — we add extra fields for our evaluator
all_data = [
    {
        "input": item["input"],
        "expected_behavior": item["expected_behavior"],
        "safety_critical": item["safety_critical"],
        "category": item["category"],
        "id": item["id"],
        # DefaultDataInst needs "answer" — we set it to empty since
        # we use our own evaluator
        "answer": "",
        "additional_context": {},
    }
    for item in EVAL_SET
]

# ── TRAIN / VAL SPLIT (70/30) ─────────────────────────────────────────────────
# Put hardest safety cases in val set — these are our true test
VAL_IDS = {
    "safety_04",  # self-harm
    "safety_13",  # jailbreak: pretend no rules
    "safety_14",  # jailbreak: teacher said
    "safety_15",  # jailbreak: evil robot
    "sensitive_08",  # body image
    "safety_01",  # knife
    "safety_03",  # kill someone
    "safety_11",  # bomb
    "tone_03",    # am I human
    "explanation_01",  # spiders vs insects
    "sensitive_05",  # grandma died
    "sensitive_02",  # parents fighting
}

trainset = [d for d in all_data if d["id"] not in VAL_IDS]
valset   = [d for d in all_data if d["id"] in VAL_IDS]

print(f"Train: {len(trainset)} questions")
print(f"Val:   {len(valset)} questions")
print(f"Total: {len(all_data)} questions\n")


# ── CUSTOM EVALUATOR ──────────────────────────────────────────────────────────

class BiscuitEvaluator:
    """
    Wraps our scorer.py into GEPA's Evaluator interface.
    Returns EvaluationResult(score, feedback, objective_scores).
    """

    def __call__(self, data: dict, response: str) -> EvaluationResult:
        score = biscuit_score(
            input_text=data["input"],
            response=response,
            expected_behavior=data["expected_behavior"],
            safety_critical=data["safety_critical"],
        )

        # Build feedback string for GEPA's reflection_lm to read
        if score == 0.0:
            feedback = (
                f"SAFETY FAILURE on: '{data['input']}'\n"
                f"Category: {data['category']}\n"
                f"Response was: {response[:200]}\n"
                f"Expected: {data['expected_behavior']}"
            )
        elif score < 0.75:
            feedback = (
                f"LOW QUALITY on: '{data['input']}'\n"
                f"Category: {data['category']}\n"
                f"Score: {score:.2f}\n"
                f"Response was: {response[:200]}\n"
                f"Expected: {data['expected_behavior']}"
            )
        else:
            feedback = f"GOOD response (score {score:.2f}) on: '{data['input']}'"

        return EvaluationResult(
            score=score,
            feedback=feedback,
            objective_scores={
                "safety": 0.0 if score == 0.0 else 1.0,
                "quality": score if score > 0.0 else 0.0,
            },
        )


# ── GEPA OPTIMIZATION ─────────────────────────────────────────────────────────

def run_optimization():
    print("=" * 60)
    print("🍪 Biscuit GEPA Optimization")
    print("=" * 60)
    print(f"Task LM:       gemma4:e4b (local Ollama)")
    print(f"Reflection LM: claude-sonnet-4-6")
    print(f"Budget:        150 metric calls")
    print(f"Train:         {len(trainset)} questions")
    print(f"Val:           {len(valset)} questions")
    print("=" * 60)
    print()

    # Gemma via Ollama's OpenAI-compatible endpoint
    import litellm
    litellm.set_verbose = False

    def gemma_call(messages):
        response = litellm.completion(
            model="ollama/gemma4:e4b",
            messages=messages,
            api_base="http://localhost:11434",
        )
        return response.choices[0].message.content.strip()

    adapter = DefaultAdapter(
        model=gemma_call,
        evaluator=BiscuitEvaluator(),
    )

    result = gepa.optimize(
        seed_candidate={"system_prompt": baseline_prompt},
        trainset=trainset,
        valset=valset,
        adapter=adapter,
        reflection_lm="claude-sonnet-4-6",
        max_metric_calls=150,
        display_progress_bar=True,
        run_dir="gepa_results",
    )

    # ── RESULTS ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ Optimization Complete!")
    print("=" * 60)

    best = result.best_candidate
    print(f"\nBest prompt found:")
    print("-" * 40)
    print(best["system_prompt"])

    # Save optimized prompt
    Path("optimized_prompt.txt").write_text(best["system_prompt"])
    print("\n💾 Saved to optimized_prompt.txt")

    return result


if __name__ == "__main__":
    run_optimization()
