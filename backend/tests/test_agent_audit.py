from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import agent_audit
from app.services.chat_processor import classify_request_type


class FakeQuery:
    def __init__(self, table: str, writes: list[tuple[str, str, dict]]):
        self.table = table
        self.writes = writes
        self.payload = {}
        self.operation = ""

    def insert(self, payload):
        self.operation, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.operation, self.payload = "update", payload
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        self.writes.append((self.table, self.operation, self.payload))
        return SimpleNamespace(data=[])


class FakeSupabase:
    def __init__(self):
        self.writes: list[tuple[str, str, dict]] = []

    def table(self, name: str):
        return FakeQuery(name, self.writes)


def test_classify_web_research_request():
    assert classify_request_type("ช่วยหารีวิวจาก Google Maps", "crm") == "web_research"
    assert classify_request_type("ค้นเอกสารบริษัท", "kb") == "knowledge"
    assert classify_request_type("ยอดขายเดือนนี้", "crm") == "crm"


@pytest.mark.asyncio
async def test_emit_agent_event_is_sequenced_and_redacted(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(agent_audit, "get_supabase_client", lambda: fake)
    agent_audit._sequences.clear()

    await agent_audit.emit_agent_event(
        run_id="run-1",
        request_id="00000000-0000-0000-0000-000000000001",
        event_type="tool",
        event_name="search_leads",
        status="completed",
        metadata={"email": "person@example.com", "count": 2},
    )
    await agent_audit.emit_agent_event(
        run_id="run-1",
        request_id="00000000-0000-0000-0000-000000000001",
        event_type="run",
        event_name="run.completed",
        status="completed",
    )

    inserts = [item for item in fake.writes if item[0] == "ai_agent_events"]
    assert [item[2]["sequence_no"] for item in inserts] == [1, 2]
    assert inserts[0][2]["metadata"]["email"] != "person@example.com"
