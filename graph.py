from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from memory import save_memory,get_first_user_query
from logger import save_log
import json
import dateparser
from datetime import datetime
from llm_config import get_llm
from web_search import web_search
import time
from pydantic import ValidationError

from schemas import IntentResult, LeaveDetails

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
    memory: dict = {}


def detect_intent_with_llm(query: str) -> str:
    prompt = f"""
You are an intent classifier for an Enterprise AI Copilot.

Classify the user query into exactly one intent.

Allowed intents:
greeting, thanks, bye,
policy,
apply_leave, leave_balance, leave_history, pending_leaves, cancel_leave, approve_leave, reject_leave,
create_ticket, ticket_status, view_all_tickets, assign_ticket, resolve_ticket,
request_asset, asset_status, approve_asset_manager, approve_asset_it, inventory_status,
memory_query,
web_search,
out_of_scope

Rules:
- If user wants leave, absence, sick leave, casual leave, not well, fever, dental appointment, family function, or asks to take off → apply_leave.
- If user asks leave balance or remaining leaves → leave_balance.
- If user asks previous/first/last query or what they asked before → memory_query.
- If user asks HR/IT policy information → policy.
- If user has laptop, VPN, Outlook, printer, network, or software issue → create_ticket.
- If user asks their ticket status → ticket_status.
- If user asks for monitor, laptop, keyboard, mouse, VPN token, or software license as an asset → request_asset.
- If unrelated to HR, IT, assets, policies, or memory → out_of_scope.

Return ONLY valid JSON with:
intent, confidence, reason

User query:
{query}
"""

    try:
        llm = get_llm(temperature=0)
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        content = content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        parsed = IntentResult(**data)

        if parsed.confidence < 0.45:
            return "out_of_scope"

        return parsed.intent

    except Exception:
        return detect_intent_rules(query)


def detect_intent_rules(query: str) -> str:
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

    if any(word in q for word in ["how to fix", "solution", "troubleshoot", "resolve error", "error code"]):
         if any(it_word in q for it_word in ["outlook", "vpn", "printer", "network", "laptop", "software"]):
            return "web_search"

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

def detect_intent(query: str) -> str:
    return detect_intent_with_llm(query)


def router_node(state: AgentState):
    query = state["query"].lower()
    memory = state.get("memory", {})

    pending_leave = memory.get("pending_leave")

    # Only continue leave flow if query looks like missing leave details
    if pending_leave:

        continuation_keywords = [
            "may", "june", "july", "august",
            "today", "tomorrow",
            "because", "due to",
            "fever", "pain", "sick",
            "family", "function",
            "2026",
        ]

        # Detect dates/numbers
        has_number = any(char.isdigit() for char in query)

        if has_number or any(word in query for word in continuation_keywords):
            state["intent"] = "apply_leave"
            return state

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


import re
import json
import dateparser
from schemas import LeaveDetails


def parse_date_to_2026(text: str):
    try:
        parsed = dateparser.parse(
            text,
            settings={
                "PREFER_DATES_FROM": "future"
            }
        )

        if not parsed:
            return None

        # Force project/demo year as 2026 if user did not mention year
        if not re.search(r"\b20\d{2}\b", text):
            parsed = parsed.replace(year=2026)

        return parsed.strftime("%Y-%m-%d")

    except Exception as e:
        print("Date parsing error:", e)
        return None


def rule_based_leave_extract(query: str):
    q = query.lower()

    leave_type = None
    reason = None
    start_date = None
    end_date = None

    sick_words = [
        "fever", "high fever", "stomach ache", "headache", "pain",
        "not well", "sick", "ill", "doctor", "hospital", "medical",
        "dental", "appointment"
    ]

    casual_words = [
        "family function", "function", "marriage", "wedding",
        "personal work", "travel", "vacation", "event"
    ]

    if any(word in q for word in sick_words):
        leave_type = "sick"

    if any(word in q for word in casual_words):
        leave_type = "casual"

    # reason extraction
    reason_patterns = [
        r"because of (.+)",
        r"because (.+)",
        r"due to (.+)",
        r"for (.+)",
    ]

    for pattern in reason_patterns:
        match = re.search(pattern, q)
        if match:
            reason = match.group(1).strip()
            break

    if not reason:
        if leave_type == "sick":
            for word in sick_words:
                if word in q:
                    reason = word
                    break

        elif leave_type == "casual":
            for word in casual_words:
                if word in q:
                    reason = word
                    break

    # date range: from may 10 to may 12
    range_match = re.search(
        r"from\s+([a-zA-Z]+\s+\d{1,2})\s+to\s+([a-zA-Z]*\s*\d{1,2})",
        q
    )

    if range_match:
        first_date_text = range_match.group(1).strip()
        second_date_text = range_match.group(2).strip()

        # If second date is only number, reuse month from first date
        if not re.search(r"[a-zA-Z]", second_date_text):
            month = first_date_text.split()[0]
            second_date_text = f"{month} {second_date_text}"

        start_date = parse_date_to_2026(first_date_text)
        end_date = parse_date_to_2026(second_date_text)

    # date pair: may 25 and 26
    if not start_date:
        pair_match = re.search(
            r"([a-zA-Z]+)\s+(\d{1,2})\s*(and|to|-)\s*(\d{1,2})",
            q
        )

        if pair_match:
            month = pair_match.group(1)
            day1 = pair_match.group(2)
            day2 = pair_match.group(4)

            start_date = parse_date_to_2026(f"{month} {day1}")
            end_date = parse_date_to_2026(f"{month} {day2}")

    # single date: on may 24 / may 24
    if not start_date:
        single_match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}", q)

        if single_match:
            date_text = single_match.group(0)
            start_date = parse_date_to_2026(date_text)
            end_date = start_date

    return {
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
    }


def extract_leave_details(query: str):
    # First try reliable rule-based extraction
    rule_data = rule_based_leave_extract(query)

    # If rule extraction found useful data, keep it
    if any(rule_data.values()):
        return rule_data

    # Fallback to LLM extraction
    prompt = """
You are extracting leave request details for an HR system.

Return ONLY valid JSON.

JSON format:
{
  "leave_type": "sick" or "casual" or "other" or null,
  "start_date": "YYYY-MM-DD" or null,
  "end_date": "YYYY-MM-DD" or null,
  "reason": "string" or null
}

Rules:
- fever, stomach ache, headache, hospital, doctor, dental = sick
- family function, travel, marriage, vacation = casual
- If one date only, same start and end date
- If no date, return null dates
- Assume year 2026 if not provided

User query:
QUERY_PLACEHOLDER
"""

    prompt = prompt.replace("QUERY_PLACEHOLDER", query)

    try:
        llm = get_llm(temperature=0)
        response = llm.invoke(prompt)

        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip().replace("```json", "").replace("```", "").strip()

        data = json.loads(content)
        parsed = LeaveDetails(**data)

        return {
            "leave_type": parsed.leave_type,
            "start_date": parsed.start_date,
            "end_date": parsed.end_date,
            "reason": parsed.reason,
        }

    except Exception as e:
        print("Leave extraction error:", e)
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

        memory = state.get("memory", {})
        pending_leave = memory.get("pending_leave")

        # Merge previous pending leave details with current user input
        if pending_leave:
            for key in ["leave_type", "start_date", "end_date", "reason"]:
                if not details.get(key) and pending_leave.get(key):
                    details[key] = pending_leave[key]

        missing = []

        if not details.get("leave_type"):
            missing.append("leave type")

        if not details.get("start_date"):
            missing.append("start date")

        if not details.get("end_date"):
            missing.append("end date")

        if not details.get("reason"):
            missing.append("reason")

        if missing:
            memory["pending_leave"] = details
            state["memory"] = memory

            state["response"] = (
                "I need a few more details to complete your leave request.\n\n"
                f"Missing: {', '.join(missing)}"
            )
            return state

        try:
            start = datetime.strptime(details["start_date"], "%Y-%m-%d")
            end = datetime.strptime(details["end_date"], "%Y-%m-%d")
        
            if end < start:
                state["response"] = (
                    "End date cannot be earlier than start date."
                )
                return state
        
        except Exception:
            state["response"] = (
                "Invalid leave dates provided."
            )
            return state

        state["response"] = apply_leave(
            state["user_id"],
            details["leave_type"],
            details["start_date"],
            details["end_date"],
            details["reason"]
        )

        # Clear pending leave after successful submission
        memory["pending_leave"] = None
        state["memory"] = memory

        return state

    if state["intent"] == "leave_status":
        state["response"] = check_leave_status(state["user_id"])
        return state

    if state["intent"] == "approve_leave":
        parts = query.split()

        leave_id = None
        for part in parts:
            if part.isdigit():
                leave_id = int(part)
                break

        if not leave_id:
            state["response"] = (
                "Please provide leave ID.\n\n"
                "Example:\n"
                "approve leave 2"
            )
            return state

        state["response"] = approve_leave(state["user_id"], leave_id, "Approved")
        return state

    if state["intent"] == "reject_leave":
        parts = query.split()

        leave_id = None
        for part in parts:
            if part.isdigit():
                leave_id = int(part)
                break

        if not leave_id:
            state["response"] = (
                "Please provide leave ID.\n\n"
                "Example:\n"
                "reject leave 3"
            )
            return state

        state["response"] = reject_leave(state["user_id"], leave_id, "Rejected by manager")
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

    if state["intent"] == "web_search":
        state["response"] = web_search(state["query"])
        return state

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

def memory_node(state):
    query = state["query"].lower()
    memory = state.get("memory", {})

    if "first query" in query:
        first_query = memory.get("first_query")

        if not first_query:
            state["response"] = "No query found in current conversation."
        else:
            state["response"] = (
                f"Your first query in this conversation was:\n\n{first_query}"
            )

    elif "last query" in query:
        messages = memory.get("chat_history", [])

        if len(messages) < 2:
            state["response"] = "No previous query found."
        else:
            previous_query = messages[-2]
            state["response"] = (
                f"Your previous query was:\n\n{previous_query}"
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
        "web_search",
    ]:
        return "it"

    if intent == "memory_query":
       return "memory"
    
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
    workflow.add_node("memory", memory_node)
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
        "memory": "memory",
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
    workflow.add_edge("memory", END)
    workflow.add_edge("out_of_scope", END)
    
    return workflow.compile()


app_graph = build_graph()


def get_agent_and_tool(intent: str):
    if intent in ["greeting", "thanks", "bye"]:
        return "Conversation Agent", "conversation_response"

    if intent == "policy":
        return "RAG Agent", "policy_retrieval"

    if intent == "memory_query":
        return "Memory Agent", "get_first_user_query"

    if intent in [
        "apply_leave",
        "leave_status",
        "approve_leave",
        "reject_leave",
        "cancel_leave",
        "leave_balance",
        "leave_history",
        "pending_leaves",
    ]:
        return "HR Agent", intent

    if intent in [
        "create_ticket",
        "ticket_status",
        "view_all_tickets",
        "assign_ticket",
        "resolve_ticket",
        "inventory_status",
        "web_search",
    ]:
        return "IT Agent", intent

    if intent in [
        "request_asset",
        "asset_status",
        "approve_asset_manager",
        "approve_asset_it",
    ]:
        return "Asset Agent", intent

    if intent == "out_of_scope":
        return "Guardrail Agent", "scope_validation"

    return "Unknown Agent", "unknown"


def run_agent(user_id, query, memory):
    start_time = time.perf_counter()

    result = app_graph.invoke({
        "user_id": user_id,
        "query": query,
        "intent": None,
        "response": None,
        "memory": memory,
    })

    response_time = round(time.perf_counter() - start_time, 3)

    intent = result.get("intent") or "unknown"
    response = result.get("response") or "No response generated."

    agent, tool_used = get_agent_and_tool(intent)

    save_memory(user_id, "last_query", query)

    save_log(
        user_id=user_id,
        query=query,
        intent=intent,
        agent=agent,
        tool_used=tool_used,
        response=response,
        response_time=response_time
    )
    save_memory(user_id, "user_query", query)
    save_memory(user_id, "last_query", query)

    return response

if __name__ == "__main__":
    print(run_agent("EMP001", "What is the notice period policy?"))
    print("-" * 50)
    print(run_agent("EMP001", "apply leave sick 2026-05-10 2026-05-10 fever"))
    print("-" * 50)
    print(run_agent("EMP001", "raise ticket Laptop laptop is overheating"))