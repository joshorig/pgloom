from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from pgloom.memory import InMemoryMemoryStore, MemoryEntry, NullMemoryStore
from pgloom.memory_postgres import PostgresMemoryStore


def test_null_memory_store_noops() -> None:
    store = NullMemoryStore()
    entry = MemoryEntry(workflow_id="wf1", key="a", value="b")
    store.put(entry)
    assert store.get("wf1", "a") is None
    assert store.list_for_workflow("wf1") == []
    assert not store.delete("wf1", "a")


def test_in_memory_store_round_trip_and_scope() -> None:
    store = InMemoryMemoryStore()
    first = MemoryEntry(workflow_id="wf1", key="a", value="1")
    second = MemoryEntry(workflow_id="wf2", key="a", value="2")
    store.put(first)
    store.put(second)
    assert store.get("wf1", "a") == first
    assert store.list_for_workflow("wf1") == [first]
    assert store.delete("wf1", "a")
    assert store.get("wf1", "a") is None


def test_in_memory_store_concurrent_puts() -> None:
    store = InMemoryMemoryStore()

    def put(index: int) -> None:
        store.put(MemoryEntry(workflow_id="wf", key=str(index), value=str(index)))

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(put, range(20)))
    assert len(store.list_for_workflow("wf")) == 20


def test_postgres_memory_store_round_trip_search_and_scope(database_url: str) -> None:
    store = PostgresMemoryStore(database_url=database_url)
    first = MemoryEntry(workflow_id="wf1", key="a", value="alpha database migration")
    second = MemoryEntry(workflow_id="wf1", key="b", value="beta deployment")
    other = MemoryEntry(workflow_id="wf2", key="a", value="alpha hidden")
    store.put(first)
    store.put(second)
    store.put(other)

    assert store.get("wf1", "a") == first
    assert store.list_for_workflow("wf1") == [first, second]
    assert store.search("wf1", "alpha", limit=5) == [first]
    assert store.search(None, "alpha", limit=5) == [first, other]
    assert store.delete("wf1", "a")
    assert store.get("wf1", "a") is None
