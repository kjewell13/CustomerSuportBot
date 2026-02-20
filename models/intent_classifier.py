from models.intent import Intent

# classify will be replaced with LLM calls after testing
class IntentClassifier():
    @staticmethod
    def classify(text: str) -> Intent:

        message = text.lower()


        if any(word in message for word in ("refund", "money back")):
            return Intent.REFUND_ORDER
        if any(word in message for word in ("order", "info", "status", "shipping")):
            return Intent.GET_ORDER_INFORMATION
        if any(word in message for word in ("human", "representative", "manager", "boss")):
            return Intent.ESCALATE_TO_HUMAN
        
        if any(word in message for word in ("hi", "hello", "hey")):
            return Intent.GREETING
        if any(word in message for word in ("bye", "goodbye")):
            return Intent.GOODBYE
        
        # if none of those passes work, just return unknown intent
        return Intent.UNKNOWN