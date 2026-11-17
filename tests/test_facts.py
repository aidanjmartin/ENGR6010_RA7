"""facts.yaml must hold exactly these values, so a typo cannot reach the screen."""
from __future__ import annotations

import re

EXPECTED = {
    "saycan_instructions": 101,
    "saycan_results": {
        "palm_saycan": {"plan": 84, "execute": 74},
        "flan_saycan": {"plan": 70, "execute": 61},
        "palm_alone": {"plan": 67},
        "flan_alone": {"plan": 38},
        "behavioral_cloning": {"plan": 0, "execute": 0},
    },
    "rt2_unseen_avg": {"rt2_palix_55b": 62, "rt1": 32},
    "rt2_trials": 6000,
    "rt2_rate": {"model_55b_hz": [1, 3], "model_5b_hz": 5},
    "l2r_tasks": 17,
    "l2r_success": {"l2r": 90, "code_as_policies_baseline": 50},
    "clip_pairs": 400_000_000,
    "clip_zero_shot": "matches original ResNet-50 on ImageNet, zero-shot",
    "homerobot_real": 20,
    "gorilla_base": {"model": "LLaMA-7B", "training": "retriever-aware",
                     "apibench": ["HuggingFace", "TorchHub", "TensorHub"]},
    "vllm_throughput": [2, 4],
    "vllm_structured": ["guided_json", "guided_regex", "guided_choice", "guided_grammar"],
    "rma_rates": {"base_policy_hz": 100, "adaptation_hz": 10},
    "rudin_train_time": {"flat_minutes_under": 4, "rough_minutes": 20, "gpus": 1},
    "cladera_specs": 7,
    "cladera_max_distance": 1200,
    "cladera_triage": {"ground_alone": 0.0, "air_ground": 83.3, "air_ground_runs": [5, 6],
                       "ground_true_map": 100.0},
    "cladera_llm": "GPT-4o through an API, not onboard",
    "tello_ports": {"command": 8889, "state": 8890, "video": 11111},
    "tello_go_limits": {"xyz_min": -500, "xyz_max": 500, "speed_min": 10, "speed_max": 100,
                        "not_all_within": 20},
    "tello_flight_time": 13,
    "go2_real_runs": {"success": 14, "runs": 19, "rate": 0.737, "std": 0.101},
    "go2_nav_rate": 10,
    "go2_walk": {"inputs": 45, "outputs": 12, "policy_hz": 50, "pd_hz": 200, "simulation_only": True},
    "owlv2_rate": 1,
    "grounding_eval": [
        {"prompt": "all prompts", "success": 0.614, "n": 132},
        {"prompt": "go to the {color} chair", "success": 0.851, "n": 67},
        {"prompt": "go to the table", "success": 0.960, "n": 25},
        {"prompt": "go to the chair (no color)", "success": 0.000, "n": 15},
        {"prompt": "go to the person", "success": 0.000, "n": 25},
    ],
    "red_chair_checks": {"hits": 180, "total": 180},
    "home_gpu": {"name": "NVIDIA RTX 4000 Ada", "memory_gb": 20},
}

# The on-screen text that carries each headline number.
EXPECTED_TEXT = {
    "tello_flight_time": "13 min",
    "go2_nav_rate": "10 Hz",
    "owlv2_rate": "about 1 Hz",
    "clip_pairs": "400 million",
    "homerobot_real": "20%",
    "cladera_max_distance": "about 1.2 km",
    "saycan_instructions": "101",
    "l2r_tasks": "17",
    "cladera_specs": "7",
    "home_gpu": "RTX 4000 Ada, 20 GB",
}
EXPECTED_TEXTS = {
    ("saycan_results", "palm_plan"): "84%", ("saycan_results", "palm_exec"): "74%",
    ("rt2_unseen_avg", "rt2"): "62%", ("rt2_unseen_avg", "rt1"): "32%",
    ("rt2_rate", "short_55b"): "1 to 3 Hz", ("l2r_success", "l2r"): "90%", ("l2r_success", "cap"): "50%",
    ("rma_rates", "base"): "100 Hz", ("rma_rates", "adapt"): "10 Hz",
    ("cladera_triage", "ground_alone"): "0%", ("cladera_triage", "air_ground"): "83.3%",
    ("cladera_triage", "runs"): "5 of 6", ("cladera_triage", "true_map"): "100%",
    ("tello_ports", "cmd"): "8889", ("tello_ports", "state"): "8890", ("tello_ports", "video"): "11111",
    ("go2_real_runs", "short"): "14 of 19", ("go2_real_runs", "rate"): "0.737 ± 0.101",
    ("go2_walk", "policy"): "50 Hz", ("go2_walk", "pd"): "200 Hz", ("go2_walk", "io"): "45 inputs → 12 joint targets",
    ("red_chair_checks", "short"): "180 of 180", ("grounding_eval", "threshold"): "0.3 m",
    ("grounding_eval", "color_chair"): "0.851", ("grounding_eval", "zero"): "0.000",
}


def check_facts(F) -> list[str]:
    problems = []
    for key, val in EXPECTED.items():
        if key not in F.facts:
            problems.append(f"missing fact {key}")
            continue
        got = F.facts[key].get("value")
        if got != val:
            problems.append(f"{key}: expected {val!r}, got {got!r}")
        if not F.facts[key].get("source"):
            problems.append(f"{key}: no source")
    for key, txt in EXPECTED_TEXT.items():
        if F.facts[key].get("text") != txt:
            problems.append(f"{key} text: expected {txt!r}, got {F.facts[key].get('text')!r}")
    for (key, part), txt in EXPECTED_TEXTS.items():
        got = F.facts[key].get("texts", {}).get(part)
        if got != txt:
            problems.append(f"{key}.{part}: expected {txt!r}, got {got!r}")
    if F.facts["grounding_eval"].get("threshold_m") != 0.3:
        problems.append("grounding_eval threshold must be 0.3 m")
    if F.mission["reserve_pct"] != 30:
        problems.append("mission reserve_pct must be 30")
    return problems


def test_facts_match_table():
    from core.facts import Facts
    assert check_facts(Facts()) == []


def test_every_template_resolves_and_no_em_dash():
    from core.facts import Facts, all_on_screen_strings
    strings = all_on_screen_strings(Facts())
    assert len(strings) > 100
    for s in strings:
        assert "\u2014" not in s, f"em dash in on-screen text: {s!r}"
        assert "{" not in s or s == "go to the {color} chair", f"unfilled template: {s!r}"


def test_no_addresses_serials_or_network_names():
    from core.facts import Facts, all_on_screen_strings
    ip = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")
    for s in all_on_screen_strings(Facts()):
        assert not ip.search(s), s
        low = s.lower()
        for word in ("ssid", "serial", "mac address", "password"):
            assert word not in low, s


MODEL_NAMES = ["RT-2", "RT-1", "OWLv2", "GPT-4o", "Go2", "LLaMA-7B", "ResNet-50"]


def test_captions_have_no_bare_numbers_outside_facts():
    """Captions are templates: any digit in a caption must come from a {fact}."""
    from core.facts import Facts
    F = Facts()
    for key, beat in F.beats.items():
        for cap in beat.get("caption", []) + beat.get("phase_captions", []):
            stripped = re.sub(r"\{[^}]*\}", "", cap)
            for name in MODEL_NAMES:
                stripped = stripped.replace(name, "")
            assert not re.search(r"\d", stripped), f"beat {key}: hard-coded number in caption {cap!r}"


def test_readme_is_generated_from_facts_and_has_no_em_dash():
    import os
    from core.facts import Facts
    from tools.make_readme import render
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    text = open(path, encoding="utf-8").read()
    assert text == render(Facts()), "README.md is stale: run python tools/make_readme.py"
    assert "\u2014" not in text
