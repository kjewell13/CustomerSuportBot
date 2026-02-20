# creates the response based on what the intent of client's message is
# again will be replaced by llm calls
from models.intent_classifier import IntentClassifier
from models.intent import Intent
from models.message import Message


class MessageCreator:
    @staticmethod
    def get_message(text: str) -> Message:
        

        intent = IntentClassifier.classify(text)

        # make text for unkown reponse here, will be overriden if not unknown
        response = "I'm not sure what you are asking, can you try to be more specific?"

        if(intent == Intent.GREETING):
            response = "Hello, What Can I help you with today?"
        if(intent == Intent.REFUND_ORDER):
            response = "Sure I can help with a refund, just enter your order ID please."
        if(intent == Intent.GET_ORDER_INFORMATION):
            response = "Enter your order id, and what information you need (ie: order status)"
        if(intent == Intent.ESCALATE_TO_HUMAN):
            response = "Let me send you to a representative now."
        if(intent == Intent.GOODBYE):
            response = "Goodbye!"

        return Message(response, intent)
        
        
