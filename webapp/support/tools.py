"""Module 6: read-only tools. The model proposes a call; code validates, authorizes and runs it."""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ORDERS_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.json"
TOOL_ROUTES = {"use_tool", "ask_clarifying_question", "handoff", "unsupported"}
# The whole tool registry. Every tool is read-only; there is no code that could change an order.
TOOLS = {"order_status": {"order_reference"}}
ORDER_FORMAT = re.compile(r"ORD-\d{4}")
STATUSES = {"processing", "in_transit", "delivered", "cancelled"}
ORDER_KEYS = {"order_reference", "customer_id", "status", "carrier", "estimated_delivery",
              "delivered_on", "updated_at"}
MAX_LOOKUPS = 5      # per browser session
MAX_AUDIT = 20
SOURCE = "Fictional order system (read-only)"

REPLIES = {
    "sign_in_required": "Sign in to look up an order. I can only show orders on your own account.",
    "invalid_arguments": "Order numbers look like ORD-1001. Please check the number and ask again.",
    # Denied and not found share one reply, so a lookup never reveals another customer's order.
    "denied": "I could not find that order on your account. Check the number, or a support professional can help.",
    "not_found": "I could not find that order on your account. Check the number, or a support professional can help.",
    "rate_limited": "Too many order lookups in this session. A support professional can help.",
}
CLARIFY = "What is the order number? It looks like ORD-1001."
HANDOFF = "A support professional needs to review this. No action has been completed."
UNSUPPORTED = "I can look up the status of your orders. I cannot help with that request here."


@dataclass(frozen=True)
class ToolResult:
    tool: str
    order_reference: str
    decision: str          # allowed, sign_in_required, invalid_arguments, denied, not_found, rate_limited
    record: dict | None = None
    checked_at: str = ""

    def as_dict(self) -> dict:
        return {"tool": self.tool, "order_reference": self.order_reference, "decision": self.decision,
                "record": self.record, "checked_at": self.checked_at, "source": SOURCE}


@dataclass(frozen=True)
class Orders:
    customers: dict
    records: dict


def load_orders(path: Path = ORDERS_PATH) -> Orders:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"customers", "orders"}:
        raise ValueError(f"{path.name}: expected customers and orders")
    customers = data["customers"]
    records = {}
    for row in data["orders"]:
        if not isinstance(row, dict) or set(row) != ORDER_KEYS:
            raise ValueError(f"{path.name}: order keys differ")
        ref = row["order_reference"]
        if not ORDER_FORMAT.fullmatch(ref) or ref in records:
            raise ValueError(f"{path.name}: invalid or duplicate order {ref}")
        if row["customer_id"] not in customers or row["status"] not in STATUSES:
            raise ValueError(f"{path.name}: {ref} has an unknown customer or status")
        datetime.fromisoformat(row["updated_at"])
        records[ref] = row
    return Orders(customers, records)


@functools.cache
def get_orders() -> Orders:
    return load_orders()


def parse_tool_request(raw: str) -> dict:
    """The model may only name a registered tool with exactly its arguments."""
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Model did not return valid JSON") from exc
    if not isinstance(result, dict) or set(result) != {"route", "tool", "arguments"}:
        raise ValueError("Tool request keys differ")
    route, tool, arguments = result["route"], result["tool"], result["arguments"]
    if route not in TOOL_ROUTES or not isinstance(tool, str) or not isinstance(arguments, dict):
        raise ValueError("Invalid tool request")
    if route == "use_tool":
        if tool not in TOOLS:
            raise ValueError("Unknown tool")
        if set(arguments) != TOOLS[tool] or any(not isinstance(v, str) or len(v) > 40 for v in arguments.values()):
            raise ValueError("Tool arguments differ")
    elif tool or arguments:
        raise ValueError("Only use_tool may name a tool")
    return result


def run_tool(request: dict, *, customer: str, lookups: int, orders: Orders | None = None,
             now: datetime | None = None) -> ToolResult:
    """Permission checks happen here, in code, on every call; the model's request is only a proposal."""
    orders = orders or get_orders()
    tool = request["tool"]
    ref = request["arguments"]["order_reference"].strip().upper()
    if customer not in orders.customers:
        return ToolResult(tool, ref, "sign_in_required")
    if not ORDER_FORMAT.fullmatch(ref):
        return ToolResult(tool, "", "invalid_arguments")
    if lookups >= MAX_LOOKUPS:
        return ToolResult(tool, ref, "rate_limited")
    record = orders.records.get(ref)
    if record is None:
        return ToolResult(tool, ref, "not_found")
    if record["customer_id"] != customer:
        return ToolResult(tool, ref, "denied")
    checked = (now or datetime.now(timezone.utc)).isoformat(timespec="minutes")
    public = {k: v for k, v in record.items() if k != "customer_id"}
    return ToolResult(tool, ref, "allowed", public, checked)


def describe(result: ToolResult) -> str:
    """The customer reply is written by code from the system record, never by the model."""
    if result.decision != "allowed":
        return REPLIES[result.decision]
    r = result.record
    status = {
        "processing": "being prepared and has not shipped yet",
        "in_transit": f"in transit with {r['carrier']}",
        "delivered": f"marked as delivered on {r['delivered_on']}",
        "cancelled": "shown as cancelled in the order system",
    }[r["status"]]
    reply = f"Order {r['order_reference']} is {status}."
    if r["estimated_delivery"] and r["status"] in ("processing", "in_transit"):
        reply += f" Estimated delivery: {r['estimated_delivery']}."
    return reply + f" Last updated {r['updated_at'][:10]}."


def audit_entry(result: ToolResult, customer: str, now: datetime | None = None) -> dict:
    """IDs and decisions only: no message text and no order details."""
    return {"at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
            "customer": customer or "not signed in", "tool": result.tool,
            "order_reference": result.order_reference or "(invalid)", "decision": result.decision}
