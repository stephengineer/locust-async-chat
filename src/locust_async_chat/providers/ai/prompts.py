"""
Prompt templates for AI message generation.
"""

# Topic generation prompt
TOPIC_GENERATION_PROMPT = """Generate a realistic conversation topic for a customer service chatbot.
The topic should be relevant to a business that offers appointments, services, and customer support.

Return only the topic name and a brief description in this format:
Topic: [topic name]
Description: [brief description]

Examples:
Topic: appointment_booking
Description: Customer wants to book a new appointment

Topic: service_inquiry
Description: Customer is asking about available services

Generate a new topic:"""

# Initial message generation prompt
INITIAL_MESSAGE_PROMPT_TEMPLATE = """You are a customer interacting with a customer service chatbot.
You want to start a conversation about: {topic_description}

Generate a natural, conversational first message that a real customer would send.
Keep it concise (1-2 sentences) and realistic.

Topic: {topic_name}
Description: {topic_description}

Your message:"""

# Follow-up message generation prompt
FOLLOW_UP_MESSAGE_PROMPT_TEMPLATE = """You are a customer having a conversation with a customer service chatbot.

Conversation topic: {topic_description}

Conversation history:
{conversation_history}

The chatbot just responded with:
"{assistant_response}"

Generate a natural follow-up message that continues the conversation.
Keep it concise (1-2 sentences) and realistic. Make sure it's related to the topic.

Your next message:"""


def format_conversation_history(messages: list) -> str:
    """
    Format conversation messages for prompt inclusion.

    Args:
        messages: List of Message objects

    Returns:
        Formatted conversation history string
    """
    formatted = []
    for msg in messages:
        role_label = "Customer" if msg.role == "user" else "Chatbot"
        formatted.append(f"{role_label}: {msg.content}")
    return "\n".join(formatted)
