import json
import traceback
from chatbot.models import Message
from shared.supabase_client import get_client


def load_history(session_id: str) -> list[Message] | None:
    try:
        client = get_client()
        result = (
            client.table("chat_sessions")
            .select("history")
            .eq("session_id", session_id)
            .execute()
        )
        if result.data:
            raw = result.data[0]["history"]
            return [Message(**m) for m in raw]
    except Exception:
        traceback.print_exc()
    return None


def save_history(session_id: str, history: list[Message]) -> None:
    try:
        client = get_client()
        history_json = [m.model_dump() for m in history]

        existing = (
            client.table("chat_sessions")
            .select("id")
            .eq("session_id", session_id)
            .execute()
        )

        if existing.data:
            client.table("chat_sessions").update({
                "history": json.loads(json.dumps(history_json)),
                "updated_at": "now()",
            }).eq("session_id", session_id).execute()
        else:
            client.table("chat_sessions").insert({
                "session_id": session_id,
                "history": json.loads(json.dumps(history_json)),
            }).execute()
    except Exception:
        traceback.print_exc()


def delete_history(session_id: str) -> None:
    try:
        client = get_client()
        client.table("chat_sessions").delete().eq("session_id", session_id).execute()
    except Exception:
        traceback.print_exc()
