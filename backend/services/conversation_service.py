"""Persistent multi-turn conversation history stored in Supabase."""
from typing import Any, Dict, List, Optional
from backend.config import settings
from backend.services.supabase_service import supabase_service


class ConversationService:
    async def add_turn(self, session_id: Optional[str], role: str, content: str) -> None:
        if not session_id or not content:
            return
        if role not in {"user", "assistant"}:
            raise ValueError(f"Rol de conversación no permitido: {role}")
        await supabase_service.ensure_session(session_id)
        await supabase_service.rest(
            "POST",
            "/rest/v1/conversation_turns",
            json={"session_id": session_id, "role": role, "content": content},
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
        )

    async def history(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        if not session_id:
            return []
        result = await supabase_service.rest(
            "GET",
            "/rest/v1/conversation_turns",
            params={
                "select": "role,content,created_at",
                "session_id": f"eq.{session_id}",
                "order": "id.desc",
                "limit": str(settings.CONVERSATION_MAX_TURNS * 2),
            },
        )
        return list(reversed(result or []))

    async def format_history(
        self, session_id: Optional[str], max_turns: Optional[int] = None
    ) -> str:
        turns = await self.history(session_id)
        limit = max_turns or settings.CONVERSATION_MAX_TURNS
        turns = turns[-limit * 2 :]
        if not turns:
            return ""
        labels = {"user": "Usuario", "assistant": "Nexo"}
        return "\n".join(
            f"{labels.get(turn['role'], turn['role'])}: {turn['content'].strip()}"
            for turn in turns
        )

    async def clear(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        await supabase_service.rest(
            "DELETE",
            "/rest/v1/conversation_turns",
            params={"session_id": f"eq.{session_id}"},
        )


conversation_service = ConversationService()
