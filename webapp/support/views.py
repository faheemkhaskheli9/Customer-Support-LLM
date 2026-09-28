"""Server-rendered course UI with CSRF-protected mutations."""

from __future__ import annotations

from pathlib import Path

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .gateway import get_gateway
from .evaluation import run_offline_evaluation
from .service import active_state, agent_turn, process_turn
from .state import correct_fact, is_expired

POLICY = (Path(__file__).resolve().parents[1] / "data" / "approved_policy.txt").read_text(encoding="utf-8")
AGENT = 5
STAGES = {  # insertion order is nav order: the main agent first, then the lessons
    AGENT: ("Support agent", "All four modules in one conversation"),
    1: ("First model call", "One message, support rules, and usage measurements"),
    2: ("Multi-turn chat", "Bounded conversation context and controlled failures"),
    3: ("Prompt routing", "Versioned instructions, validated JSON, and handoff routes"),
    4: ("Safe memory", "Fact corrections, review, retention, expiry, and deletion"),
}
HISTORY_KEYS = {2: "m2_history", 3: "m3_history", AGENT: "agent_history"}


def back(request):
    """State forms are shared by Module 4 and the agent; return to whichever sent them."""
    return redirect(f"/?stage={AGENT if request.POST.get('stage') == str(AGENT) else 4}")


def home(request):
    try:
        stage = int(request.GET.get("stage", AGENT))
    except ValueError:
        stage = AGENT
    if stage not in STAGES:
        stage = AGENT
    state = active_state(request.session) if stage in (4, AGENT) else None
    if stage == 4:
        request.session.pop("m2_history", None)
        request.session.pop("m3_history", None)
    return render(request, "support/home.html", {
        "stage": stage, "stages": STAGES, "stage_title": STAGES[stage][0], "agent": AGENT,
        "history": request.session.get(HISTORY_KEYS.get(stage, ""), []),
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
        if stage == AGENT:
            turn = agent_turn(message=request.POST.get("message", ""), session=request.session,
                              gateway=get_gateway(), policy=POLICY)
        else:
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
    return back(request)


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
    return back(request)


@require_POST
def delete_state(request):
    request.session.pop("m4_state", None)
    request.session.pop("m2_history", None)
    request.session.pop("m3_history", None)
    request.session.pop("agent_history", None)
    request.session.pop("last_result", None)
    request.session["notice"] = "Course session state removed from this server-side session."
    return back(request)


@require_POST
def reset(request, stage: int):
    if stage == 2:
        request.session.pop("m2_history", None)
    elif stage == 3:
        request.session.pop("m3_history", None)
    elif stage in (4, AGENT):
        request.session.pop("m4_state", None)
        if stage == AGENT:
            request.session.pop("agent_history", None)
    request.session.pop("last_result", None)
    return redirect(f"/?stage={stage if stage in STAGES else AGENT}")
