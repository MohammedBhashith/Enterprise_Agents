from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from memory import save_memory
from logger import save_log
import json
import dateparser
from datetime import datetime
from llm_config import get_llm

from rbac import validate_user_or_message
from rag import answer_policy_question
from tools import (
    apply_leave,
    check_leave_status,
    approve_leave,
    create_ticket,
    check_ticket_status,
    request_asset,
    approve_asset_manager,
    approve_asset_it,
    get_leave_balance,
    view_leave_history,
    view_pending_leaves,
    cancel_leave,
    reject_leave,
    view_all_tickets,
    assign_ticket,
    get_inventory_status,
    resolve_ticket,
    check_asset_request_status,
)


class AgentState(TypedDict):
    user_id: str
    query: str
    intent: Optional[str]
    response: Optional[str]


def detect_intent(query: str) -> str:
    q = query.lower().strip()

    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    thanks = ["thanks", "thank you", "thankyou", "thx"]
    bye_words = ["bye", "goodbye", "see you", "exit"]

    if q in greetings:
     return "greeting"

    if q in thanks:
     return "thanks"

    if q in bye_words:
     return "bye"
    
    if any(phrase in q for phrase in [
        "leave balance",
        "remaining leave",
        "remaining leaves",
        "my balance",
        "how many leaves do i have"
    ]):
        return "leave_balance"

    if any(phrase in q for phrase in [
        "leave history",
        "applied leaves",
        "my leaves",
        "view leaves"
    ]):
        return "leave_history"

    if any(phrase in q for phrase in [
        "pending leave",
        "pending requests",
        "pending leave requests"
    ]):
        return "pending_leaves"
    
    # Leave
    if any(phrase in q for phrase in [
        "apply leave",
        "request leave",
        "i need leave",
        "take leave",
        "i want leave",
        "i want sick leave",
        "i want casual leave",
        "need sick leave",
        "need casual leave",
        "leave on",
        "leave from"
    ]):
        return "apply_leave"

    # HR / Policy
    if any(phrase in q for phrase in [
        "policy", "notice period", "casual leave", "sick leave",
        "work from home", "maternity", "how many leaves",
        "total leaves", "leave allowed"
    ]):
        return "policy"

    

    if any(phrase in q for phrase in [
        "leave status", "my leave", "leave history", "pending leave"
    ]):
        return "leave_status"

    if "approve leave" in q:
        return "approve_leave"
    
    if "reject leave" in q:
        return "reject_leave"

    if "cancel leave" in q:
        return "cancel_leave"
    

    if any(phrase in q for phrase in [
        "all tickets",
        "view all tickets",
        "show all tickets"
    ]):
        return "view_all_tickets"

    if "assign ticket" in q:
        return "assign_ticket"

    if "resolve ticket" in q:
        return "resolve_ticket"

    if any(phrase in q for phrase in [
        "inventory status",
        "show inventory",
        "available assets"
    ]):
        return "inventory_status"
    
    if any(phrase in q for phrase in [
    "asset status",
    "my asset",
    "my assets",
    "track asset"
    ]):
      return "asset_status"

    if any(phrase in q for phrase in [
        "request asset",
        "need monitor",
        "need laptop",
        "need keyboard",
        "need mouse",
        "need vpn token",
        "need software license",
        "i need a monitor",
        "i need a laptop",
    ]):
        return "request_asset"

    # IT (natural language supported)
    if any(phrase in q for phrase in [
        "laptop", "vpn", "outlook", "email issue",
        "printer", "network", "software", "install"
    ]):
        return "create_ticket"

    if "ticket status" in q or "my ticket" in q:
        return "ticket_status"

    # Asset
    if any(phrase in q for phrase in [
    "request asset",

    "need monitor", "need laptop", "need keyboard", "need mouse",
    "need vpn", "need vpn token", "need software", "need license",

    "i need a monitor", "i need a laptop", "i need a keyboard", "i need a mouse",
    "i need vpn", "i need vpn token", "i need software", "i need license",

    "require monitor", "require laptop", "require keyboard", "require mouse",
    ]):
     return "request_asset"

    if "manager approve asset" in q:
        return "approve_asset_manager"

    if "it approve asset" in q:
        return "approve_asset_it"

    # 🚨 Guardrail (important)
    return "out_of_scope"


def router_node(state: AgentState):
    state["intent"] = detect_intent(state["query"])
    return state


def rbac_node(state: AgentState):
    valid, message = validate_user_or_message(state["user_id"])

    if not valid:
        state["response"] = message

    return state

def greeting_node(state: AgentState):
    state["response"] = (
        "Hello! I am your Enterprise AI Copilot. "
        "I can help you with HR policies, leave requests, IT tickets, and asset requests."
    )
    return state


def thanks_node(state: AgentState):
    state["response"] = "You're welcome! Let me know if you need help with HR or IT support."
    return state


def bye_node(state: AgentState):
    state["response"] = "Goodbye! Have a great day."
    return state




def policy_node(state: AgentState):
    state["response"] = answer_policy_question(state["user_id"], state["query"])
    return state



def extract_leave_details(query: str):
    """
    Extract leave details from natural language.
    Uses LLM only for structured extraction.
    """

    prompt = f"""
Extract leave details from the user query.

Return ONLY valid JSON.
No explanation.

Required JSON fields:
leave_type: sick/casual/other/null
start_date: YYYY-MM-DD/null
end_date: YYYY-MM-DD/null
reason: string/null

Rules:
- If only one date is mentioned, use same date for start_date and end_date.
- If year is missing, assume 2026.
- If leave type is not clear, return null.
- If reason is not clear, return null.

User query:
{query}
"""

    try:
        llm = get_llm(temperature=0)
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        content = content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        return {
            "leave_type": data.get("leave_type"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "reason": data.get("reason"),
        }

    except Exception:
        return {
            "leave_type": None,
            "start_date": None,
            "end_date": None,
            "reason": None,
        }

def hr_node(state: AgentState):
    query = state["query"].lower()

    if state["intent"] == "apply_leave":
        details = extract_leave_details(state["query"])

        missing = []

        if not details["leave_type"]:
            missing.append("leave type")

        if not details["start_date"]:
            missing.append("start date")

        if not details["end_date"]:
            missing.append("end date")

        if not details["reason"]:
            missing.append("reason")

        if missing:
            state["response"] = (
                "I need a few more details to apply your leave.\n\n"
                f"Missing: {', '.join(missing)}\n\n"
                "Example:\n"
                "I want sick leave on May 5 because I have fever."
            )
            return state

        state["response"] = apply_leave(
            state["user_id"],
            details["leave_type"],
            details["start_date"],
            details["end_date"],
            details["reason"]
        )
        return state

    if state["intent"] == "leave_status":
        state["response"] = check_leave_status(state["user_id"])
        return state

    if state["intent"] == "approve_leave":
        # format: approve leave 1
        parts = query.split()

        if len(parts) < 3:
            state["response"] = (
                    "Please provide leave ID.\n\n"
                    "Example:\n"
                    "approve leave 2"
                )
            return state

        leave_id = int(parts[2])
        state["response"] = approve_leave(state["user_id"], leave_id, "Approved")
        return state
    
    if state["intent"] == "leave_balance":
        state["response"] = get_leave_balance(state["user_id"])
        return state

    if state["intent"] == "leave_history":
        state["response"] = view_leave_history(state["user_id"])
        return state

    if state["intent"] == "pending_leaves":
        state["response"] = view_pending_leaves(state["user_id"])
        return state


    if state["intent"] == "reject_leave":
        parts = query.split()

        leave_id = None
        for part in parts:
            if part.isdigit():
                leave_id = int(part)
                break

        if not leave_id:
            state["response"] = "Please mention the leave ID to reject. Example: reject leave 3"
            return state

        state["response"] = reject_leave(state["user_id"], leave_id, "Rejected by manager")
        return state

    if state["intent"] == "cancel_leave":
        parts = query.split()

        leave_id = None
        for part in parts:
            if part.isdigit():
                leave_id = int(part)
                break

        if not leave_id:
            state["response"] = (
                "Please provide a leave ID.\n\n"
                "Example:\n"
                "cancel leave 2"
            )
            return state

        state["response"] = cancel_leave(state["user_id"], leave_id)
        return state

    state["response"] = "HR agent could not understand the request."
    return state


def extract_issue_from_query(query: str):
    q = query.lower()

    if "laptop" in q:
        return "Laptop", query

    if "vpn" in q:
        return "VPN", query

    if "outlook" in q or "email" in q:
        return "Outlook", query

    if "printer" in q:
        return "Printer", query

    if "network" in q:
        return "Network", query

    if "software" in q or "install" in q:
        return "Software", query

    return None, None

def out_of_scope_node(state):
    state["response"] = (
        "I’m designed to assist only with internal HR and IT operations.\n\n"
        "You can ask things like:\n"
        "- HR policies\n"
        "- Leave requests\n"
        "- IT issues (laptop, VPN, email)\n"
        "- Asset requests"
    )
    return state

def extract_issue_from_query(query: str):
    q = query.lower()

    if "laptop" in q:
        return "Laptop", query

    if "vpn" in q:
        return "VPN", query

    if "outlook" in q or "email" in q:
        return "Outlook", query

    if "printer" in q:
        return "Printer", query

    if "network" in q:
        return "Network", query

    if "software" in q or "install" in q:
        return "Software", query

    return None, None


def extract_asset_from_query(query: str):
    q = query.lower()

    asset_map = {
        "laptop": "Laptop",
        "monitor": "Monitor",
        "keyboard": "Keyboard",
        "mouse": "Mouse",
        "vpn token": "VPN Token",
        "vpn": "VPN Token",
        "software license": "Software License",
        "license": "Software License",
    }

    for keyword, asset_type in asset_map.items():
        if keyword in q:
            return asset_type, query

    return None, None

def it_node(state: AgentState):
    query = state["query"].lower()

    if state["intent"] == "view_all_tickets":
        state["response"] = view_all_tickets(state["user_id"])
        return state

    if state["intent"] == "inventory_status":
        state["response"] = get_inventory_status(state["user_id"])
        return state

    if state["intent"] == "assign_ticket":
        parts = query.split()
        ticket_id = None
        engineer_id = None

        for part in parts:
            if part.isdigit():
                ticket_id = int(part)
            elif part.upper().startswith("IT"):
                engineer_id = part.upper()

        if not ticket_id or not engineer_id:
            state["response"] = "Please provide ticket ID and engineer ID.\n\nExample:\nassign ticket 1 IT001"
            return state

        state["response"] = assign_ticket(state["user_id"], ticket_id, engineer_id)
        return state

    if state["intent"] == "resolve_ticket":
        parts = query.split()
        ticket_id = None

        for part in parts:
            if part.isdigit():
                ticket_id = int(part)
                break

        if not ticket_id:
            state["response"] = "Please provide ticket ID.\n\nExample:\nresolve ticket 1"
            return state

        state["response"] = resolve_ticket(state["user_id"], ticket_id)
        return state

    if state["intent"] == "ticket_status":
        state["response"] = check_ticket_status(state["user_id"])
        return state

    if state["intent"] == "create_ticket":
        issue_type, description = extract_issue_from_query(state["query"])

        if not issue_type:
            state["response"] = (
                "Please mention the issue type clearly, such as Laptop, VPN, Outlook, Printer, Network, or Software."
            )
            return state

        state["response"] = create_ticket(
            state["user_id"],
            issue_type,
            description,
            "Medium"
        )
        return state

    if state["intent"] == "request_asset":
      asset_type, reason = extract_asset_from_query(state["query"])

      if not asset_type:
          state["response"] = (
              "Please mention the asset clearly.\n\n"
              "Supported: Laptop, Monitor, Keyboard, Mouse, VPN Token, Software License"
          )
          return state
  
      state["response"] = request_asset(
          state["user_id"],
          asset_type,
          reason
      )
      return state

    if state["intent"] == "asset_status":
      state["response"] = check_asset_request_status(state["user_id"])
      return state

    if state["intent"] == "approve_asset_manager":
        parts = query.split()

        if len(parts) < 4:
            state["response"] = "Please use this format: manager approve asset 1"
            return state

        request_id = int(parts[3])
        state["response"] = approve_asset_manager(state["user_id"], request_id, "Approved")
        return state

    if state["intent"] == "approve_asset_it":
        parts = query.split()

        if len(parts) < 4:
            state["response"] = "Please use this format: it approve asset 1"
            return state

        request_id = int(parts[3])
        state["response"] = approve_asset_it(state["user_id"], request_id, "Approved")
        return state

    state["response"] = "IT agent could not understand the request."
    return state


def unknown_node(state: AgentState):
    state["response"] = (
        "I’m sorry, I can currently help only with HR and IT operations. "
        "You can ask me about HR policies, leave requests, IT tickets, or asset requests.\n\n"
        "Examples:\n"
        "- What is the notice period policy?\n"
        "- How many casual leaves are allowed?\n"
        "- I have an issue in my laptop\n"
        "- My VPN is not connecting\n"
        "- request asset Monitor need second screen"
    )
    return state


def route_after_rbac(state):
    if state.get("response"):
        return "end"

    intent = state["intent"]

    if intent == "greeting":
        return "greeting"

    if intent == "thanks":
        return "thanks"

    if intent == "bye":
        return "bye"

    if intent == "policy":
        return "policy"

    if intent in [
    "apply_leave",
    "leave_status",
    "approve_leave",
    "cancel_leave",
    "leave_balance",
    "leave_history",
    "pending_leaves",
     "reject_leave",]:
        return "hr"

    if intent in [
        "ticket_status",
        "create_ticket",
        "request_asset",
        "approve_asset_manager",
        "approve_asset_it",
        "view_all_tickets",
        "assign_ticket",
        "resolve_ticket",
        "inventory_status",
        "asset_status",
    ]:
        return "it"
    
    return "out_of_scope"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("rbac", rbac_node)
    workflow.add_node("policy_rag_agent", policy_node)
    workflow.add_node("hr_agent", hr_node)
    workflow.add_node("it_agent", it_node)
    workflow.add_node("unknown", unknown_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("thanks", thanks_node)
    workflow.add_node("bye", bye_node)
    workflow.add_node("out_of_scope", out_of_scope_node)

    workflow.set_entry_point("router")

    workflow.add_edge("router", "rbac")

    workflow.add_conditional_edges(
        "rbac",
        route_after_rbac,
        {
        "greeting": "greeting",
        "thanks": "thanks",
        "bye": "bye",
        "policy": "policy_rag_agent",
        "hr": "hr_agent",
        "it": "it_agent",
        "out_of_scope": "out_of_scope",
        "unknown": "unknown",
        "end": END,
        }
    )

    workflow.add_edge("policy_rag_agent", END)
    workflow.add_edge("hr_agent", END)
    workflow.add_edge("it_agent", END)
    workflow.add_edge("unknown", END)
    workflow.add_edge("greeting", END)
    workflow.add_edge("thanks", END)
    workflow.add_edge("bye", END)
    workflow.add_edge("out_of_scope", END)
    
    return workflow.compile()


app_graph = build_graph()


def run_agent(user_id: str, query: str) -> str:
    result = app_graph.invoke({
        "user_id": user_id,
        "query": query,
        "intent": None,
        "response": None,
    })

    intent = result.get("intent") or "unknown"
    response = result.get("response") or "No response generated."

    save_memory(user_id, "last_query", query)
    save_log(
        user_id=user_id,
        query=query,
        agent=intent,
        tool_used=intent,
        response=response
    )

    return response


if __name__ == "__main__":
    print(run_agent("EMP001", "What is the notice period policy?"))
    print("-" * 50)
    print(run_agent("EMP001", "apply leave sick 2026-05-10 2026-05-10 fever"))
    print("-" * 50)
    print(run_agent("EMP001", "raise ticket Laptop laptop is overheating"))