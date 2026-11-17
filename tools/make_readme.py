"""Write README.md from the template below, filling every number from content/facts.yaml.

    python tools/make_readme.py

tests/test_facts.py checks that README.md matches this output, so the cheat
sheet can never disagree with the screen.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.facts import Facts  # noqa: E402

TEMPLATE = """# One Sentence, Two Robots

An in-class presentation program for ENGR 6010 (AI in Robotics): LLM mission
control for a quadruped and a drone from one home PC. About 5 minutes of talking,
11 beats, one point per beat.

The one idea: the LLM plans; it never drives the motors. It turns one sentence
into typed tool calls for robots that already have their own controllers, a
checker rejects any call that breaks a limit, and open-vocabulary vision ties the
words to places. A drone's view from above is what makes a ground robot's search
work.

## Install and run

```bash
python3 -m venv .venv && source .venv/bin/activate     # Python 3.10 or newer
pip install -r requirements.txt
python main.py
```

| Flag | Effect |
|---|---|
| `--windowed` | 1600 x 900 resizable window (default) |
| `--fullscreen` | full screen at the desktop resolution |
| `--act N` | start at act N (0 to 5) |
| `--check` | offline self-check, prints PASS or FAIL |
| `--screenshots OUTDIR` | render every beat and step at seven window sizes, verify alignment, exit |

Nothing is downloaded and nothing needs a network. Every frame is drawn on one
1920 x 1080 virtual canvas and scaled uniformly into the window with letterbox
bars, so windowed and full screen show the same layout at different sizes.

## Before class

1. Turn Wi-Fi off and run `python main.py --check`. Every line should say PASS.
2. Run `python main.py --fullscreen` on the projector.
3. Press `D`, go to beat 2.2 (press `2`, then Space), and drag the battery
   slider. The crosshair must sit exactly on the pointer. Press `D` again to hide it.

## Controls

| Key or input | Action |
|---|---|
| Space or Right | next beat, or next step inside a stepped beat |
| Left | previous beat or step |
| 0 to 5 | jump to act |
| R | replay the current beat |
| [ and ] | step the battery slider in 2.2 |
| mouse drag | battery slider in 2.2 |
| F | toggle full screen |
| D | alignment debug overlay (crosshair, window size, scale, offset) |
| H | help overlay |
| I | hide or show the beat indicator |
| Esc | quit |

## Presenter cheat sheet (about 30 seconds per beat)

If time runs short, skip **2.2** first, then **4.1**.

| Beat | Say this | Point at |
|---|---|---|
| 0.1 Title | One sentence typed at one home PC sends a drone and a dog out together and brings them back. | the sentence typing in |
| 1.1 Two bodies | The drone flies and looks; the dog walks to a place. The planner has to split one sentence across both. | {tello_flight_time} per battery; the phrases flying to each card |
| 1.2 Clock ladder | Language belongs at the slowest layer. Learned policies and controllers do the fast work. Learned walking policies like this train in simulation in minutes on one GPU (Rudin et al.: flat {rudin_train_time.flat}, rough {rudin_train_time.rough}), and Tan et al. showed sim-to-real transfer. | RT-2 55B at {rt2_rate.short_55b}; my walking policy {go2_walk.policy} and PD loop {go2_walk.pd} (simulation only) |
| 2.1 Interface ladder | Pick the rung your robots already have controllers for. Ours is typed tool calls. | SayCan plan {saycan_results.palm_plan}, execute {saycan_results.palm_exec} on {saycan_instructions} instructions |
| 2.2 Say x Can (skip first) | Run the step that is both useful and possible. Drag the battery below the reserve and the choice flips to "fly home". | the {reserve}% reserve line |
| 3.1 Checker | The LLM proposes; a checker decides. Step through the three bad calls. | "x outside {tello_go_limits.xyz} (Tello SDK)" |
| 3.2 Words to places | Open-vocabulary vision ties words to pixels, but measure it: two phrases fail outright. | {grounding_eval.color_chair} for "go to the {{color}} chair" vs {grounding_eval.zero} for "the chair" and "the person"; {red_chair_checks.short} on the real robot |
| 4.1 Why a drone (skip second) | Seen from above, the ground search went from failing to mostly working. | {cladera_triage.ground_alone} to {cladera_triage.air_ground} ({cladera_triage.runs}) |
| 4.2 One home point | Everything that thinks stays on the home PC; the robots carry out commands. Solid boxes are built and measured, dashed are plans. | {go2_real_runs.short} real runs reached the target |
| 4.3 Mission | Step through seven phases: the drone looks, the dog goes, both come home, and every call passed the checker. | the battery gauge crossing toward the {reserve}% reserve |
| 5.1 Close | Three takeaways, then what is built and what is next. | "{go2_real_runs.short} real runs" in the built column |

## Limits, stated plainly

* No LLM runs in this program. The mission sentence and the tool calls are canned,
  typed by hand in `content/mission.yaml`, and tagged "Canned example, no LLM running".
* The tool checker (`team/checker.py`) is real code. It validates each call against
  `content/tools.schema.json` with `jsonschema`, checks the Tello SDK limits, a
  geofence, a battery reserve, and whether a target has been found. The reserve
  ({reserve}%) and the geofence are my settings, not values from any paper.
* Beats 2.2, 3.2 (left side), and 4.3 are illustrations: made-up scores, a drawn
  embedding space, and scripted motion. They are tagged "Illustration".
* Plans, not yet built: the Tello link, the LLM server on the home PC, the
  two-robot mission, the no-router setup (one Wi-Fi interface per robot hotspot),
  and the learned-dynamics safety filter.
* The learned walking policy ran in simulation only. On the real robot, Unitree's
  own walking controller does the walking, driven by velocity targets over WebRTC.
* No rate or latency is shown for the LLM, the Tello flight controller, or
  Unitree's walking controller, because none was measured.
* Every other number is as reported in the papers below or measured in my Exam 2
  repository, and each one is stored once, with its source, in `content/facts.yaml`.

## Tests

```bash
python -m pytest -q
python main.py --screenshots out/
```

* `tests/test_facts.py`: every value in `facts.yaml` matches the provenance table;
  no em dashes, IP addresses, serial numbers, or network names on screen; no
  hard-coded numbers in captions; this README matches `tools/make_readme.py`.
* `tests/test_checker.py`: the six canned calls pass in the state where they are
  issued; the three bad calls fail with exactly the on-screen reasons; Tello edge
  cases (x = 500 accepted, 501 rejected, x = y = z = 10 rejected, speed 9 and 101
  rejected); the Say x Can choice follows the battery.
* `tests/test_mission.py`: the drone stays above the reserve until its return leg,
  both robots end on the pad, every logged call passed the checker, and no path
  leaves the geofence.
* `tests/test_layout.py`: every text block and UI element in every beat and step
  sits at least 40 px inside the canvas with no overlapping text; the mouse mapping
  inverts the present step (including Retina scaling); the slider drags correctly
  through the real mapping; `--check` passes with sockets disabled.
* The screenshot harness presents every beat and step into 1280 x 720, 1600 x 900,
  1920 x 1080, 2560 x 1440, 1920 x 1200, 1440 x 900, and 1366 x 768 through the real
  present step, crops each to its content, scales it back, and compares it to the
  canvas. A frame shifted by even a few pixels fails the alignment check.

## References

Ahn et al. 2022 (SayCan, arXiv:2204.01691) · Liang et al. 2022 (Code as Policies,
arXiv:2209.07753) · Yu et al. 2023 (Language to Rewards, arXiv:2306.08647) · Huang
et al. 2023 (VoxPoser, arXiv:2307.05973) · Brohan et al. 2023 (RT-2,
arXiv:2307.15818) · Patil et al. 2023 (Gorilla, arXiv:2305.15334) · Kwon et al.
2023 (vLLM, arXiv:2309.06180) and the vLLM Structured Outputs documentation ·
Radford et al. 2021 (CLIP, arXiv:2103.00020) · Yenamandra et al. 2023 (HomeRobot,
arXiv:2306.11565) · Kumar et al. 2021 (RMA, arXiv:2107.04034) · Rudin et al. 2021
(arXiv:2109.11978) · Tan et al. 2018 (arXiv:1804.10332) · Cladera et al. 2025
(arXiv:2505.09108) · Vaswani et al. 2017 (Attention Is All You Need) · Ryze Tello
SDK User Guide and User Manual.

Also used or relevant, not shown on screen: ONNX, Netron, ROS 2,
`unitree_sdk2_python`, the community `go2_robot` ROS 2 stack,
`unitree_webrtc_connect`, and the Kine2Go dataset (Pałucki, Siwak, Ciebiera, et al.,
2026, arXiv:2606.14433).
"""


def render(F: Facts) -> str:
    return F.fmt(TEMPLATE)


def main():
    F = Facts()
    path = os.path.join(ROOT, "README.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(F))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
