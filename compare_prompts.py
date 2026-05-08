"""
compare_prompts.py — Baseline vs Optimized Prompt Comparison
-------------------------------------------------------------
Runs both prompts against all 39 eval questions and produces
a side-by-side score comparison.

Run: python compare_prompts.py
"""

import json
import ollama
from pathlib import Path
from collections import defaultdict

from eval_set import EVAL_SET
from scorer import score as biscuit_score

# ── LOAD PROMPTS ──────────────────────────────────────────────────────────────
baseline_prompt    = Path("baseline_prompt.txt").read_text()
optimized_prompt   = Path("final_prompt.txt").read_text()

MODEL = "gemma4:e4b"

# ── RUN EVALUATION ────────────────────────────────────────────────────────────

def evaluate_prompt(prompt: str, prompt_name: str) -> list[dict]:
    """Run all 39 eval questions against a prompt and return scored results."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {prompt_name}")
    print(f"{'='*60}")

    results = []
    for i, item in enumerate(EVAL_SET):
        print(f"\n[{i+1}/{len(EVAL_SET)}] {item['id']}: {item['input'][:50]}...")

        # Get Gemma's response
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": item["input"]},
            ]
        )
        gemma_response = response["message"]["content"]

        # Score it
        s = biscuit_score(
            input_text=item["input"],
            response=gemma_response,
            expected_behavior=item["expected_behavior"],
            safety_critical=item["safety_critical"],
        )

        results.append({
            "id": item["id"],
            "category": item["category"],
            "input": item["input"],
            "safety_critical": item["safety_critical"],
            "response": gemma_response,
            "score": s,
        })

    return results


# ── ANALYSIS ──────────────────────────────────────────────────────────────────

def analyze(results: list[dict], name: str) -> dict:
    """Compute summary statistics from scored results."""
    scores = [r["score"] for r in results]
    safety_scores = [r["score"] for r in results if r["safety_critical"]]
    non_safety_scores = [r["score"] for r in results if not r["safety_critical"]]

    by_category = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(r["score"])

    failures = [r for r in results if r["score"] == 0.0]

    return {
        "name": name,
        "overall_avg": sum(scores) / len(scores),
        "safety_avg": sum(safety_scores) / len(safety_scores) if safety_scores else 0,
        "quality_avg": sum(non_safety_scores) / len(non_safety_scores) if non_safety_scores else 0,
        "by_category": {k: sum(v)/len(v) for k, v in by_category.items()},
        "failures": failures,
        "total": len(scores),
    }


def print_comparison(baseline_stats: dict, optimized_stats: dict):
    """Print a clean side-by-side comparison."""
    print("\n" + "="*60)
    print("📊 COMPARISON RESULTS")
    print("="*60)

    def delta(a, b):
        d = b - a
        arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
        return f"{arrow} {abs(d):.3f}"

    print(f"\n{'Metric':<25} {'Baseline':>10} {'Optimized':>10} {'Change':>10}")
    print("-" * 55)
    print(f"{'Overall Average':<25} {baseline_stats['overall_avg']:>10.3f} {optimized_stats['overall_avg']:>10.3f} {delta(baseline_stats['overall_avg'], optimized_stats['overall_avg']):>10}")
    print(f"{'Safety Average':<25} {baseline_stats['safety_avg']:>10.3f} {optimized_stats['safety_avg']:>10.3f} {delta(baseline_stats['safety_avg'], optimized_stats['safety_avg']):>10}")
    print(f"{'Quality Average':<25} {baseline_stats['quality_avg']:>10.3f} {optimized_stats['quality_avg']:>10.3f} {delta(baseline_stats['quality_avg'], optimized_stats['quality_avg']):>10}")

    print(f"\n{'By Category':}")
    print("-" * 55)
    all_cats = set(baseline_stats["by_category"]) | set(optimized_stats["by_category"])
    for cat in sorted(all_cats):
        b = baseline_stats["by_category"].get(cat, 0)
        o = optimized_stats["by_category"].get(cat, 0)
        print(f"  {cat:<23} {b:>10.3f} {o:>10.3f} {delta(b, o):>10}")

    print(f"\n{'Safety Failures':}")
    print("-" * 55)
    print(f"  Baseline:  {len(baseline_stats['failures'])} failures")
    for f in baseline_stats["failures"]:
        print(f"    ❌ {f['id']}: {f['input'][:50]}")
    print(f"  Optimized: {len(optimized_stats['failures'])} failures")
    for f in optimized_stats["failures"]:
        print(f"    ❌ {f['id']}: {f['input'][:50]}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🍪 Biscuit Prompt Comparison")
    print("This will take ~10-15 minutes (scoring 78 responses total)")
    print("Do not close this terminal!\n")

    # Run both evaluations
    baseline_results  = evaluate_prompt(baseline_prompt, "BASELINE")
    optimized_results = evaluate_prompt(optimized_prompt, "OPTIMIZED")

    # Analyze
    baseline_stats  = analyze(baseline_results, "Baseline")
    optimized_stats = analyze(optimized_results, "Optimized")

    # Print comparison
    print_comparison(baseline_stats, optimized_stats)

    # Save full results
    output = {
        "baseline": baseline_results,
        "optimized": optimized_results,
        "baseline_stats": {k: v for k, v in baseline_stats.items() if k != "failures"},
        "optimized_stats": {k: v for k, v in optimized_stats.items() if k != "failures"},
    }
    Path("comparison_results.json").write_text(json.dumps(output, indent=2))
    print("\n💾 Full results saved to comparison_results.json")
