# handles state of convsersation, acts as 'memory' for bot in each conversation

from models.intent import Intent
from dataclasses import dataclass, field

from typing import Optional

# instantated on a per connection basis, stored in db (sqlite -> eventually ling term like postgres)

'''

field(default_factory={type})
- every time object of this class is instantiated, then create an empty attribute of {type} type

'''
@dataclass
class ChatState:
    chat_history: list = field(default_factory=list)
    current_intent: Optional[Intent] = None 
    pending_data: Optional[str] = None            # like user_id used for state preservation across messages with same intent (refund)
    user_data: dict  = field(default_factory=dict)        # like {"user_id" : "123"}

