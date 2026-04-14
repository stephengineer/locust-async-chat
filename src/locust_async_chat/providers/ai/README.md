# AI Provider Architecture

## Overview

The AI Provider module generates conversational messages dynamically using LLM instead of static examples from LangSmith. It maintains conversation context per user and generates topic-related messages that flow naturally based on SUT responses.

## Architecture

```
ai_provider/
├── __init__.py              # Module exports
├── topic_manager.py         # Topic selection and management
├── message_generator.py     # LLM-based message generation
├── conversation_context.py  # Conversation history tracking
├── prompts.py               # Prompt templates
└── ai_provider.py           # Main provider interface
```

## Components

### 1. TopicManager (`topic_manager.py`)

Manages conversation topics:
- **Predefined topics**: 8 default topics (appointment_booking, service_inquiry, pricing_question, etc.)
- **Selection strategies**: `random` or `round_robin`
- **Custom topics**: Can add custom topics programmatically

**Usage:**
```python
topic_manager = TopicManager(selection_strategy="random")
topic = topic_manager.select_topic()
```

### 2. MessageGenerator (`message_generator.py`)

Generates messages using OpenAI LLM:
- **Initial messages**: Generated from selected topic
- **Follow-up messages**: Generated based on conversation history + SUT response
- **Configurable**: Model, temperature, max_tokens

**Usage:**
```python
generator = MessageGenerator(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=150
)
message = generator.generate_initial_message(topic_name, topic_description)
```

### 3. ConversationContext (`conversation_context.py`)

Tracks conversation state per user/conversation:
- **Message history**: Stores user and assistant messages
- **Topic tracking**: Maintains topic for conversation
- **Turn counting**: Tracks conversation turns
- **Thread-safe**: ConversationContextManager handles multiple conversations

**Usage:**
```python
context = context_manager.get_or_create_context(conversation_id)
context.add_user_message("Hello")
context.add_assistant_message("Hi, how can I help?")
```

### 4. AIMessageProvider (`ai_provider.py`)

Main provider interface (compatible with LangSmithExampleProvider):
- **Topic selection**: Selects topic for new conversations
- **Message generation**: Generates initial and follow-up messages
- **Context management**: Maintains conversation context per conversation_id
- **Compatibility**: Implements `next()` method for easy integration

**Usage:**
```python
provider = AIMessageProvider()
provider.initialize()

# First message (selects topic automatically)
message1 = provider.next_message(conversation_id="conv-123")

# Follow-up message (uses conversation history)
message2 = provider.next_message(
    conversation_id="conv-123",
    assistant_response="I can help with that..."
)
```

## Integration Flow

### 1. Initialization (locustfile.py)

```python
if config.message_provider == "ai":
    topic_manager = TopicManager(selection_strategy=config.topic_selection_strategy)
    message_generator = MessageGenerator(
        model=config.ai_model,
        temperature=config.ai_temperature,
        max_tokens=config.ai_max_tokens
    )
    ai_provider = AIMessageProvider(
        topic_manager=topic_manager,
        message_generator=message_generator
    )
    ai_provider.initialize()
    set_ai_provider(ai_provider)
```

### 2. User Flow (user.py)

```python
# Get next message
if config.message_provider == "ai":
    example = ai_provider.next_message(
        conversation_id=self.conversation_id,
        assistant_response=self.last_assistant_response
    )
else:
    example = langsmith_provider.next()

# Send to SUT
payload = MessagePayload(..., text=example.question)

# Store SUT response for next message
if callback.response_text:
    self.last_assistant_response = callback.response_text
```

## Configuration

### Environment Variables

```bash
LOADTEST_MESSAGE_PROVIDER=ai              # "langsmith" or "ai"
LOADTEST_AI_MODEL=gpt-4o-mini             # OpenAI model name
LOADTEST_AI_TEMPERATURE=0.7                # 0.0-2.0
LOADTEST_AI_MAX_TOKENS=150                 # Max tokens per message
LOADTEST_TOPIC_SELECTION_STRATEGY=random   # "random" or "round_robin"
```

### CLI Arguments

```bash
uv run locust -f src/locust_async_chat/locustfile.py \
  --message-provider ai \
  --ai-model gpt-4o-mini \
  --ai-temperature 0.7 \
  --ai-max-tokens 150 \
  --topic-selection-strategy random
```

## Predefined Topics

1. **appointment_booking** - Booking or rescheduling appointments
2. **service_inquiry** - Asking about services offered
3. **pricing_question** - Questions about pricing and packages
4. **cancellation_request** - Requesting to cancel a service
5. **technical_support** - Technical issues or troubleshooting
6. **product_recommendation** - Asking for product recommendations
7. **account_management** - Managing account settings
8. **feedback_complaint** - Providing feedback or complaints

## Custom Topics

You can add custom topics programmatically:

```python
from locust_async_chat.providers.ai import TopicManager, Topic

topic_manager = TopicManager()
custom_topic = Topic(
    name="custom_topic",
    description="Description of custom topic",
    category="custom"
)
topic_manager.add_topic(custom_topic)
```

## Conversation Flow Example

1. **User starts** → Topic selected (e.g., "appointment_booking")
2. **First message** → LLM generates: "I'd like to book an appointment for next week"
3. **SUT responds** → "What day works best for you?"
4. **Second message** → LLM generates: "How about Tuesday afternoon?"
5. **SUT responds** → "Tuesday at 2pm is available"
6. **Third message** → LLM generates: "Perfect, let's book that"

Each message is contextually related to the topic and previous conversation.

## Benefits

1. **Dynamic conversations**: Messages adapt to SUT responses
2. **Topic consistency**: All messages in a conversation relate to the same topic
3. **Realistic flow**: Natural conversation progression
4. **Configurable**: Easy to adjust model, temperature, topics
5. **Compatible**: Works alongside LangSmith provider (switch via config)

## Limitations

1. **API costs**: Each message requires an LLM API call
2. **Latency**: LLM generation adds latency (can be mitigated with caching)
3. **Rate limits**: Subject to OpenAI API rate limits
4. **Determinism**: Messages vary due to temperature setting
