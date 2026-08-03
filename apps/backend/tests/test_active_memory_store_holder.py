import inspect
from app.services.active_memory_store_holder import AuthoritativeActiveMemoryStoreHolder
from app.store.active_memory_store import InMemoryActiveMemoryStore

def test_holder_never_exposes_raw_store_and_publishes_by_generation():
    holder=AuthoritativeActiveMemoryStoreHolder(); replacement=InMemoryActiveMemoryStore()
    holder.publish(replacement,0,1)
    assert holder.current_generation()==1
    assert not any(name in vars(holder.__class__) for name in ("read","mutate","store"))
    assert not isinstance(holder.snapshot_payload(),InMemoryActiveMemoryStore)
