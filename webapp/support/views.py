"""Server-rendered course UI with CSRF-protected mutations."""

from __future__ import annotations

from pathlib import Path

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .gateway import get_gateway
from .evaluation import run_offline_evaluation
from .service import active_state, process_turn
from .state import correct_fact, is_expired

POLICY = (Path(__file__).resolve().parents[1] / "data" / "approved_policy.txt").read_text(encoding="utf-8")
STAGES = {
    1: ("First model call", "One message, support rules, and usage measurements"),
    2: ("Multi-turn chat", "Bounded conversation context and controlled failures"),
    3: ("Prompt routing", "Versioned instructions, validated JSON, and handoff routes"),
    4: ("Safe memory", "Fact corrections, review, retention, expiry, and deletion"),
}


def home(request):
    try:
        stage = int(request.GET.get("stage", "1"))
    except ValueError:
        stage = 1
    if stage not in STAGES:
        stage = 1
    state = active_state(request.session) if stage == 4 else None
    if stage == 4:
        request.session.pop("m2_history", None)
        request.session.pop("m3_history", None)
    return render(request, "support/home.html", {
        "stage": stage, "stages": STAGES, "stage_title": STAGES[stage][0],
        "history": request.session.get("m2_history", []) if stage == 2 else request.session.get("m3_history", []) if stage == 3 else [],
        "state": state, "result": request.session.pop("last_result", None),
        "evaluation": request.session.pop("evaluation", None),
        "notice": request.session.pop("notice", None),
        "policy": POLICY if stage >= 3 else "",
    })


@require_POST
def chat(request, stage: int):
    if stage not in STAGES:
        return redirect("home")
    try:
        turn = process_turn(stage=stage, message=request.POST.get("message", ""),
                            session=request.session, gateway=get_gateway(),
                            policy=POLICY if stage >= 3 else "")
        request.session["last_result"] = turn.as_dict()
    except (ValueError, RuntimeError) as exc:
        request.session["notice"] = str(exc)
    return redirect(f"/?stage={stage}")


@require_POST
def evaluate(request):
    request.session["evaluation"] = run_offline_evaluation()
    return redirect("/?stage=3")


@require_POST
def correct(request):
    state = request.session.get("m4_state")
    if not state or is_expired(state):
        request.session.pop("m4_state", None)
        request.session["notice"] = "Session expired. Start a new Module 4 conversation."
    else:
        try:
            request.session["m4_state"] = correct_fact(
                state, request.POST.get("key", ""), request.POST.get("value", ""))
            request.session["notice"] = "Reported fact corrected."
        except ValueError as exc:
            request.session["notice"] = str(exc)
    return redirect("/?stage=4")


@require_POST
def retention(request):
    choice = request.POST.get("choice", "")
    if choice in ("session_only", "until_expiry"):
        state = active_state(request.session).copy()
        state["retention_choice"] = choice
        request.session["m4_state"] = state
        request.session.set_expiry(0 if choice == "session_only" else 1800)
        request.session["notice"] = "Retention preference updated for this browser session."
    else:
        request.session["notice"] = "Invalid retention choice."
    return redirect("/?stage=4")


@require_POST
def delete_state(request):
    request.session.pop("m4_state", None)
    request.session.pop("m2_history", None)
    request.session.pop("m3_history", None)
    request.session.pop("last_result", None)
    request.session["notice"] = "Course session state removed from this server-side session."
    return redirect("/?stage=4")


@require_POST
def reset(request, stage: int):
    if stage == 2:
        request.session.pop("m2_history", None)
    elif stage == 3:
        request.session.pop("m3_history", None)
    elif stage == 4:
        request.session.pop("m4_state", None)
    request.session.pop("last_result", None)
    return redirect(f"/?stage={stage if stage in STAGES else 1}")
