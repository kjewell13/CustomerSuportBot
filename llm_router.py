# llm_router.py


import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal

from openai import AsyncOpenAI
from models.intent import Intent  
from models.knowledge_search import knowledge_search
from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncOpenAI(api_key= os.getenv("OPENAI_API_KEY"))

NextAction = Literal["respond", "ask_for_slot"]
SlotName = Literal["order_id", "phone_or_email"]

@dataclass
class RouteResult:
    intent: Intent
    confidence: float
    next_action: NextAction
    slot_to_request: Optional[SlotName] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None


ROUTER_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "route",
            "description": "Classify intent and decide what the server should do next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            Intent.GREETING.value,
                            Intent.GOODBYE.value,
                            Intent.REFUND_ORDER.value,
                            Intent.GET_ORDER_INFORMATION.value,
                            Intent.ESCALATE_TO_HUMAN.value,
                            Intent.KNOWLEDGE_QA.value,
                            Intent.UNKNOWN.value,
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "next_action": {
                        "type": "string",
                        "enum": ["respond", "ask_for_slot", "call_tool"],
                    },
                    "slot_to_request": {
                        "type": ["string", "null"],
                        "enum": ["order_id", "phone_or_email", None],
                    },
                    "tool_name": {"type": ["string", "null"]},
                    "tool_args": {"type": ["object", "null"]},
                },
                "required": [
                    "intent",
                    "confidence",
                    "next_action",
                    "slot_to_request",
                    "tool_name",
                    "tool_args",
                ],
                "additionalProperties": False,
            },
        },
    }
]


routing_prompt = f"""
You are an intent router for a customer support assistant.

You MUST call the tool named "route".

Allowed intents (exact strings):
- {Intent.GREETING.value}
- {Intent.GOODBYE.value}
- {Intent.REFUND_ORDER.value}
- {Intent.GET_ORDER_INFORMATION.value}
- {Intent.ESCALATE_TO_HUMAN.value}
- {Intent.KNOWLEDGE_QA.value}
- {Intent.UNKNOWN.value}

Rules:
- If greeting/hello -> intent={Intent.GREETING.value}, next_action=respond.
- If goodbye/bye -> intent={Intent.GOODBYE.value}, next_action=respond.
- If order status/shipping/tracking -> intent={Intent.GET_ORDER_INFORMATION.value}.
- If refund/return money back -> intent={Intent.REFUND_ORDER.value}.
- If user asks policy/product/how-to -> intent={Intent.KNOWLEDGE_QA.value}.
- If user requests a human/representative -> intent={Intent.ESCALATE_TO_HUMAN.value}.
- If unclear -> intent={Intent.UNKNOWN.value}.

Slot logic:
- For GET_ORDER_INFORMATION or REFUND_ORDER:
  - If you do NOT have an order_id in state and user did not provide one, next_action=ask_for_slot and slot_to_request=order_id.
  - If user provides an order_id, you may choose next_action=call_tool with tool_name="get_order" and tool_args={{"order_id": "<id>"}}.
Be conservative: ask for missing info instead of guessing.

If STATE indicates pending_data=order_id:
- If the user message is digits (like "124"), treat it as the order_id being provided.
- Use intent=current_intent if current_intent is GET_ORDER_INFORMATION or REFUND_ORDER.
- next_action can be call_tool with get_order or respond.
"""


def build_route_state_summary(state: Any) -> str:
    # Keep it tiny for cost.
    order_id = state.user_data.get("order_id") if hasattr(state, "user_data") else None
    pending = state.pending_data if hasattr(state, "pending_data") else None
    current_intent = state.current_intent.value if hasattr(state, "current_intent") and state.current_intent else None
    return f"order_id={order_id}, pending_data={pending}, current_intent={current_intent}"


async def get_intent(user_text: str, state: Any) -> RouteResult:
    state_summary = build_route_state_summary(state)

    resp = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": routing_prompt},
            {"role": "system", "content": f"STATE: {state_summary}"},
            {"role": "user", "content": user_text},
        ],
        tools=ROUTER_TOOL,
        tool_choice="required",  # force a tool call 
    )

    msg = resp.choices[0].message
    
    tool_calls = msg.tool_calls or []
    if not tool_calls:
        return RouteResult(intent=Intent.UNKNOWN, confidence=0.0, next_action="respond")

    call = tool_calls[0]
    args = json.loads(call.function.arguments)

    # Convert returned intent string into your Intent enum
    intent = Intent(args["intent"])

    return RouteResult(
        intent=intent,
        confidence=float(args["confidence"]),
        next_action=args["next_action"],
        slot_to_request=args["slot_to_request"],
        tool_name=args["tool_name"],
        tool_args=args["tool_args"],
    )


# data class for generation message
@dataclass
class GenerationResult:
    next_action: NextAction
    response_text: Optional[str] = None
    slot_to_request: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None


GENERATE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "Fetch order details by order_id. Use this for tracking/status/refund flows "
                "once you have an order_id. Do NOT guess order details without calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID (digits or order reference)."
                    }
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": (
                "Search the local knowledge base markdown files for company/policy/warranty/repairs/contact/support-hours info. "
                "Use this for Knowledge QA and policy questions. Return top relevant snippets with their source."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the knowledge base."
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "How many top snippets to return.",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 3
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]



generate_prompt = f"""
You are a customer support assistant.

You will receive:
- STATE SUMMARY (current_intent, any known slots like order_id)
- The user's latest message

Your job:
- Respond helpfully and concisely.
- Use tools when needed.
- Never invent order details or policy details.

Tools you can call:
- get_order(order_id): Use for order status/shipping/tracking/refund flows once order_id is known.
- knowledge_search(query, top_k): Use for company info, warranty, returns, repairs, support hours, contact info, policy/how-to questions.

Rules:
1) If current_intent is GET_ORDER_INFORMATION or REFUND_ORDER:
   - If order_id is missing, ask for it plainly (no tool call).
   - If order_id is present, call get_order to retrieve details before answering.
2) If current_intent is KNOWLEDGE_QA:
   - Call knowledge_search with a focused query unless the answer is trivial.
3) If the user message is just an order ID (e.g., digits) and current_intent is order-related, treat it as the order_id and proceed.
4) If a tool returns "not_found" / error, ask the user to confirm the order ID or provide email/phone.
5) Keep responses short; ask 1 question at a time if more info is needed.
"""

def build_gen_state_summary(state) -> str:
    intent = state.current_intent.value if state.current_intent else None
    order_id = state.user_data.get("order_id")
    pending = state.pending_data
    return f"current_intent={intent}, order_id={order_id}, pending_data={pending}"


# intent passed into here in order to 
async def generate_result(user_text: str, state: Any) -> GenerationResult:
    messages= [
            {"role": "system", "content": generate_prompt},
            {"role": "system", "content": f"STATE: {build_gen_state_summary(state)}"},
            {"role": "user", "content": user_text},
    ]
    
    response1 = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        tools=GENERATE_TOOL,
    )
    
    message1 = response1.choices[0].message
    
    tool_calls = message1.tool_calls or []
    if not tool_calls:
        return GenerationResult(next_action = "respond", response_text = message1.content)
    
    # stores if tool calls are needed
    messages.append({
        "role": "assistant",
        "content": message1.content,
        "tool_calls": message1.tool_calls,
    })

    for call in tool_calls:
        tool_name = call.function.name
        tool_args = json.loads(call.function.arguments or "{}")

        if tool_name == "get_order":
            tool_output = get_order(tool_args.get("order_id", ""))
        elif tool_name == "knowledge_search":
            tool_output = knowledge_search(tool_args.get("query", ""), int(tool_args.get("top_k", 3)))
        else:
            tool_output = {"error": f"Unknown Tool: {tool_name}"}

        # append the result of tool to messages2
        messages.append({
            "role" : "tool",
            "tool_call_id" : call.id,
            "content" : json.dumps(tool_output)
        })

        # now we can perform final call based on tool result to get output

    response2 = await client.chat.completions.create(
        model = "gpt-4.1-mini",
        messages = messages
    )

    final_response = response2.choices[0].message
    return GenerationResult(next_action = "respond", response_text = final_response.content)


# tool calls that LLM can call in generate_result

# temporary 'database' for testing


FAKE_ORDERS = {
  "124": {"status": "Shipped", "eta": "2026-02-25", "carrier": "UPS", "tracking": "1Z..."},
  "555": {"status": "Processing", "eta": "2026-02-28", "carrier": None, "tracking": None},
}

def get_order(order_id: str) -> dict:
    return FAKE_ORDERS.get(order_id, {"error": "not found"})


