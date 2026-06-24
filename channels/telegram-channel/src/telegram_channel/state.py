import uuid


class ConversationState:
    def __init__(self):
        self._sessions: dict[int, dict] = {}

    def set_agent(self, chat_id: int, agent: str, user_id: int):
        self._sessions[chat_id] = {
            "agent": agent,
            "conversation_id": f"tg-{chat_id}-{uuid.uuid4().hex[:8]}",
            "session_id": f"tg-user-{user_id}",
        }

    def get_session(self, chat_id: int) -> dict | None:
        return self._sessions.get(chat_id)

    def clear_session(self, chat_id: int):
        self._sessions.pop(chat_id, None)
