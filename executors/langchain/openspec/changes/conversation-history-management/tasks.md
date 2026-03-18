## 1. History Store Setup

- [ ] 1.1 Add `from langchain_core.chat_history import ChatMessageHistory` import to `executor.py`
- [ ] 1.2 Add `self.history_store: Dict[str, ChatMessageHistory] = {}` to `LangChainExecutor.__init__`

## 2. Core History Management

- [ ] 2.1 Replace the history conversion block (lines 51-59) and first-turn check (lines 72-74) with `conversationId`-based lookup: retrieve existing history or create new one with system prompt
- [ ] 2.2 Append user message (plain or RAG-augmented) to history via `history.add_message(HumanMessage(...))`
- [ ] 2.3 Replace `chat_client.ainvoke(langchain_messages)` with `chat_client.ainvoke(history.messages)`
- [ ] 2.4 Append assistant response to history via `history.add_message(AIMessage(...))`

## 3. Cleanup

- [ ] 3.1 Remove all references to `request.history` from `executor.py`

## 4. Tests

- [ ] 4.1 Add test for new conversation: verify system prompt is prepended and user message is stored
- [ ] 4.2 Add test for existing conversation: verify history is retrieved and new messages are appended
- [ ] 4.3 Add test for RAG conversation: verify RAG-augmented message is stored in history
