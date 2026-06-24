import os
import tempfile

# Redirect the module-level store singleton to a throwaway temp file *before*
# any test module imports `app.main` (and therefore constructs the singleton).
# This guarantees tests never read or write the real project data file at
# apps/backend/data/hivemind-store.json. `setdefault` lets an explicit env
# override (e.g. CI) still win.
os.environ.setdefault(
    "HIVEMIND_STORE_PATH",
    os.path.join(tempfile.mkdtemp(prefix="hivemind-test-"), "hivemind-store.json"),
)

# Same isolation for the Phase 5A source registry persistence file.
os.environ.setdefault(
    "HIVEMIND_REGISTRY_PATH",
    os.path.join(tempfile.mkdtemp(prefix="hivemind-registry-test-"), "source-registry.json"),
)
