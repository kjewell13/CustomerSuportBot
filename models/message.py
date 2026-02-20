from dataclasses import dataclass

# automatically creates __init__ with specified feils, as well as equality, toString, 

@dataclass
class Message:
    text: str
    intent: str

    
    def __post_init__(self):
        if not self.text:
            raise ValueError("text cannot be empty")
