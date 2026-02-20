# wrapper for all of the helper classes for getting message -- called by server, and this class
# will call all other classes, message_creator(replaced by this class), intent_classifier, etc. 
from models.intent_classifier import IntentClassifier
from models.intent import Intent
from models.chat_state import ChatState

# simply manages chat state and calls stateless helpers
class ChatManager:
    @staticmethod
    def handle_client_input(message: str, state: ChatState) -> str:
        message = message.strip()

        if not message:
            return "Please ask your quesion here, can't help if you don't type anything!"
        
        # checks if we are still needing to do something, ie order lookup, 

        # if last time the pending data was user id, then this time the message send was id
        if state.pending_data == "order_id":
            state.user_data["order_id"] = message
            state.pending_slot = None

        intent = IntentClassifier.classify(message)
        state.current_intent = intent

        if(intent == Intent.GREETING):
            return "Hello, What Can I help you with today?"
        
        if(intent == Intent.GOODBYE):
            return "Goodbye!"
        
        if(intent == Intent.GET_ORDER_INFORMATION):
            state.pending_data = "order_id"
            return "Enter your order id, and what information you need (ie: order status"

        if(intent == Intent.REFUND_ORDER):
            state.pending_data = "order_id"
            return "Sure I can help with a refund, just enter your order ID please."
        
        if(intent == Intent.ESCALATE_TO_HUMAN):
            return "Let me send you to a representative now."
        
        return "I'm not sure how to help you now, can you refrase what you need assistance with?"





