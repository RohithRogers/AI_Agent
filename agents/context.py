import os
import json
from enum import Enum
from typing import List, Dict, Optional, Any

class MessageTier(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class MessageStore:
    """
    Message Store (source of truth)
    Stores full history with tier tags attached.
    """
    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def store(self, message: Dict[str, Any], tier: MessageTier):
        message["tier"] = tier.value
        self._history.append(message)

    def store_at_front(self, message: Dict[str, Any], tier: MessageTier):
        message["tier"] = tier.value
        self._history.insert(0, message)

    def get_all(self) -> List[Dict[str, Any]]:
        return self._history

    def clear(self):
        self._history = []

class ContextManager:
    """
    Implements the Context Management Workflow:
    Classifier -> Message Store -> Payload Assembler -> Summarizer -> Token Budget Enforcer
    """
    def __init__(self, model_client=None, token_budget: int = 60000, summary_threshold: int = 40000):
        self.store = MessageStore()
        self.model_client = model_client
        self.token_budget = token_budget
        self.summary_threshold = summary_threshold
        self.summary_cache: Dict[str, str] = {}
        self.window_size = 10 # Number of recent messages to always keep intact

    def update_system_prompt(self, content: str):
        """Updates the system prompt in the store."""
        for msg in self.store.get_all():
            if msg["role"] == "system":
                msg["content"] = content
                return
        # If no system prompt exists, add one at the start
        self.store.store_at_front({"role": "system", "content": content}, MessageTier.HIGH)

    def classify_message(self, role: str, content: str, msg_obj: Optional[Dict[str, Any]] = None) -> MessageTier:
        """
        Classifier: HIGH / MEDIUM / LOW
        - LOW -> discard
        - HIGH/MEDIUM -> store
        """
        if role == "system":
            return MessageTier.HIGH
            
        # Always keep tool calls and responses, even if empty text
        if msg_obj and ("tool_call_part" in msg_obj or "tool_response" in msg_obj or "tool_call" in msg_obj):
            return MessageTier.HIGH
        
        # Heuristics for classification
        content_str = str(content).strip()
        if not content_str:
            return MessageTier.LOW
            
        lower_content = content_str.lower()
        
        # High priority keywords
        high_keywords = ["error", "exception", "failed", "urgent", "critical", "bug", "fix", "important"]
        if any(kw in lower_content for kw in high_keywords):
            return MessageTier.HIGH
            
        # Medium priority: Standard dialogue, code snippets, etc.
        if len(content_str) > 100 or role == "user":
            return MessageTier.MEDIUM
            
        # Low priority: Short acknowledgments, empty tool responses, etc.
        if len(content_str) < 20 and role != "user":
            return MessageTier.LOW
            
        return MessageTier.MEDIUM

    def truncate_content(self, text: str, max_chars: int = 3000) -> str:
        """Truncates long text using head+tail strategy to preserve context."""
        text = str(text)
        if len(text) <= max_chars:
            return text
        head = 400
        tail = max_chars - head
        dropped = len(text) - max_chars
        return text[:head] + f"\n...[{dropped} chars truncated]...\n" + text[-tail:]

    def add_message(self, role: str, content: str, **kwargs):
        """
        Entry point for new messages.
        Applies Classifier logic and stores if not LOW.
        """
        message = {"role": role, "content": content}
        message.update(kwargs)
        
        tier = self.classify_message(role, content, message)
        
        if tier == MessageTier.LOW:
            # LOW -> discard
            return
            
        self.store.store(message, tier)

    def assemble_payload(self) -> List[Dict[str, Any]]:
        """
        Payload Assembler: Pulls from store, applies window + tier rules.
        """
        messages = self.store.get_all()
        # Custom rules: Always keep System prompts and recent window.
        return messages

    def summarize_old_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Summarize old msgs (cached).
        Compresses history if over the threshold.
        """
        if len(messages) <= self.window_size + 1: # +1 for system prompt
            return messages

        # Identify messages to summarize (everything before the recent window, excluding system)
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]
        
        to_summarize = other_msgs[:-self.window_size]
        recent_msgs = other_msgs[-self.window_size:]
        
        if not to_summarize:
            return messages

        # Check cache (simple implementation using hash of message IDs/content)
        cache_key = str(hash(json.dumps(to_summarize, sort_keys=True)))
        if cache_key in self.summary_cache:
            summary_content = self.summary_cache[cache_key]
        elif self.model_client:
            # Call API to summarize
            summary_content = self._request_summary(to_summarize)
            self.summary_cache[cache_key] = summary_content
        else:
            # Fallback if no client: just drop them or provide a placeholder
            summary_content = "[Previous conversation history omitted to save tokens]"

        summary_msg = {
            "role": "user", 
            "content": f"[System: Previous conversation summary: {summary_content}]",
            "tier": MessageTier.HIGH.value
        }
        
        return system_msgs + [summary_msg] + recent_msgs

    def _request_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Calls the Gemini API to generate a concise summary of the provided messages."""
        if not self.model_client:
            return "[Context summarized - Summary unavailable (No client)]"
            
        try:
            # Construct the summarization prompt
            history_text = ""
            for m in messages:
                role = m.get("role", "unknown").upper()
                content = str(m.get("content", ""))
                
                # Handle Tool Calls
                if "tool_call_part" in m:
                    tc = m["tool_call_part"]
                    content += f" [System: Calls tool '{tc.function_call.name}' with args {tc.function_call.args}]"
                
                # Handle Tool Responses
                if "tool_response" in m:
                    tr = m["tool_response"]
                    content += f" [System: Tool '{tr['name']}' returned: {str(tr['content'])[:200]}]"
                
                history_text += f"{role}: {content[:500]}\n"
            
            prompt = f"Summarize the following conversation history into a single concise paragraph. Focus only on the key facts, tasks completed, and current state of the project. Reply ONLY with the summary.\n\nCONVERSATION:\n{history_text}"
            
            # Use a fast model for summarization
            response = self.model_client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            
            if response and response.text:
                return response.text.strip()
            return "[Context summarized - Summary empty]"
        except Exception as e:
            # Fallback if the API call fails (e.g., rate limits or safety filters)
            return f"[Context summarized - API Error: {str(e)[:50]}]"

    def count_message_chars(self, msg: Dict[str, Any]) -> int:
        """Calculates total characters in a message, including tool data."""
        count = len(str(msg.get("content", "")))
        if "tool_response" in msg:
            count += len(str(msg["tool_response"].get("content", "")))
        if "tool_call_part" in msg:
            count += 100 # Estimation for tool call metadata
        return count

    def enforce_token_budget(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Token Budget Enforcer: Hard cap check, trim middle if needed.
        Keeps system messages and ensures start + end of conversation are preserved.
        """
        def count_chars(msgs):
            return sum(self.count_message_chars(m) for m in msgs)

        if count_chars(messages) <= self.token_budget:
            return messages

        # Logic to "trim middle":
        # Keep system prompts (usually high value)
        # Keep the beginning of the conversation (first few messages for context)
        # Keep the end of the conversation (most recent context)
        # Remove from the middle.
        
        system_msgs = [m for m in messages if m["role"] == "system"]
        others = [m for m in messages if m["role"] != "system"]
        
        start_index = 2 # Keep first 2 messages
        end_index = self.window_size # Keep last N messages
        
        # Iteratively remove from the middle until budget is met
        while count_chars(system_msgs + others) > self.token_budget:
            if len(others) > (start_index + end_index):
                # Standard middle trim
                others.pop(start_index)
            elif len(others) > 1:
                # If budget still exceeded, start shrinking from the front
                # (except the system prompts)
                others.pop(0)
            else:
                # Last resort: break to avoid infinite loop
                break
            
        return system_msgs + others

    def get_context(self) -> List[Dict[str, Any]]:
        """
        API Call Prep: Orchestrates the workflow.
        """
        # 1. Pull from store
        payload = self.assemble_payload()
        
        # 2. Over threshold? -> Summarize
        total_chars = sum(self.count_message_chars(m) for m in payload)
        if total_chars > self.summary_threshold:
            payload = self.summarize_old_messages(payload)
            
        # 3. Hard cap check -> Trim middle
        payload = self.enforce_token_budget(payload)
        
        # Return necessary fields for API call
        result = []
        for m in payload:
            clean_msg = {"role": m["role"], "content": m["content"]}
            # Pass through all metadata keys (tool calls, responses, attachments, etc.)
            for key, value in m.items():
                if key not in ["role", "content", "tier"]:
                    clean_msg[key] = value
            result.append(clean_msg)
        return result

# For backward compatibility if needed
class Context(ContextManager):
    def __init__(self, messages=None, mode="online", model="deepseek-coder"):
        super().__init__()
        if messages:
            for m in messages:
                self.add_message(m["role"], m["content"])
        self.mode = mode
        self.model = model

    def get_messages(self):
        return self.get_context()


