# wrapper for all of the helper classes for getting message -- called by server, and this class
# will call all other classes, message_creator(replaced by this class), intent_classifier, etc. 
from models.intent_classifier import IntentClassifier
from models.intent import Intent
from models.chat_state import ChatState
from llm_router import get_intent, generate_result


SLOT_PROMPTS = {
    "order_id": "Sure — what’s your order ID?",
    "phone_or_email": "Sure — what’s the email or phone number on the order?",
    "reason": "Got it — what’s the reason for the return (damaged, incorrect item, etc.)?",
}


# simply manages chat state and calls stateless helpers
class ChatManager:
    @staticmethod
    async def handle_client_input(message: str, state: ChatState) -> str:
        message = message.strip()

        if not message:
            return "Please ask your quesion here, can't help if you don't type anything!"
        
        # checks if we are still needing to do something, ie order lookup, 
        if state.pending_data:
            slot = state.pending_data
            state.user_data[slot] = message
            state.pending_data = None

            # now get result here instead of rerouting below
            result = await generate_result(message, state)

            # if we still need a slot, handle here -- shold only happen with bad user input or bad llm response
            if result.next_action == "ask_for_slot" and result.slot_to_request:
                state.pending_data = result.slot_to_request
                return SLOT_PROMPTS.get(result.slot_to_request, "Can you provide some more information?")
            
            return result.response_text or "Got it."
        
        intent = await get_intent(message, state)
        state.current_intent = intent.intent

        if intent.next_action == "ask_for_slot" and intent.slot_to_request:
            state.pending_data = intent.slot_to_request
            return SLOT_PROMPTS.get(intent.slot_to_request, "What more informtion can you provide so I can lookup your order?")
        
        result = await generate_result(message, state)
        if result.next_action == "ask_for_slot" and result.slot_to_request:
            state.pending_data = result.slot_to_request
            return SLOT_PROMPTS.get(result.slot_to_request, "Can you provide some more information?")
        
        return result.response_text or "Got it."



        





# previous function implementation before llm calls for testing if needed
'''
# if last time the pending data was user id, then this time the message send was id
        if state.pending_data == "order_id":
            state.user_data["order_id"] = message
            state.pending_data = None

            # handle continued intent (retrieving order status)
            if state.current_intent == Intent.GET_ORDER_INFORMATION:
                # *** get order call to db will replace following

                return (
                    f"Got it -- order ID {state.user_data['order_id']}. "
                    "What would you like to know (status, shipping, tracking, etc.)"
                )
            
            if state.current_intent == Intent.REFUND_ORDER:
                return(
                    f"Got it -- order ID {state.user_data['order_id']}. "
                    "Can you tell me the reason for return (damanged, incorrect item, etc)?"
                )
            
            # fallback if llm json repsponse doesnt set current intent
            return f"Thanks - I found your order with the ID {state.user_data['order_id']}. What can I help you with?"


        # Now route only when information is not needed -- final response
        # again -- will be replaced with llm call

        # get initial response from llm with intent
        result = get_intent(message, state)
        state.current_intent = result.intent

        # first have to check if we still need further information 
        # ---***PLACEHOLDER UNTIL GENERATE RESPONSE IMPLEMENTED****
        if result.next_action == "ask_for_slot":
            # update state 
            state.pending_data = result.slot_to_request
            if result.slot_to_request == "order_id":
                return "Sure — what’s your order ID?"
            if result.slot_to_request == "phone_or_email":
                return "Sure — what’s the email or phone number on the order?"
            return "What information can you provide to help me look that up?"

        if(result.intent == Intent.GREETING):
            return "Hello, What Can I help you with today?"
        
        if(result.intent == Intent.GOODBYE):
            return "Goodbye!"
        
        if(result.intent == Intent.GET_ORDER_INFORMATION):
            state.current_intent = Intent.GET_ORDER_INFORMATION
            state.pending_data = "order_id"
            return "Enter your order id, and what information you need (ie: order status"

        if(result.intent == Intent.REFUND_ORDER):
            state.current_intent = Intent.REFUND_ORDER
            state.pending_data = "order_id"
            return "Sure I can help with a refund, just enter your order ID please."
        
        if(result.intent == Intent.ESCALATE_TO_HUMAN):
            return "Let me send you to a representative now."
        
        return "I'm not sure how to help you now, can you refrase what you need assistance with?"
'''