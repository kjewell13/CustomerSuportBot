from enum import StrEnum, auto

class Intent(StrEnum):
    GREETING = auto() #automatically assigns lowercase version of enum
    GOODBYE = auto()
    REFUND_ORDER = auto()
    GET_ORDER_INFORMATION = auto()
    ESCALATE_TO_HUMAN = auto()
    KNOWLEDGE_QA = auto()
    UNKNOWN = auto()
    

