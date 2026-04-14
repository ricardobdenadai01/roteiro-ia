import sys
from unittest.mock import MagicMock

# The cryptography Rust DLL may be blocked by Windows App Control policies.
# Mock all external dependencies that transitively import cryptography so tests
# for pure functions can run without those native extensions.
for mod_name in [
    "cryptography", "cryptography.hazmat", "cryptography.hazmat.bindings",
    "cryptography.hazmat.bindings._rust", "cryptography.hazmat.bindings._rust.exceptions",
    "cryptography.hazmat.primitives", "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.asymmetric.ec", "cryptography.exceptions",
    "google", "google.genai", "google.genai.types",
    "google.auth", "google.auth.transport", "google.auth.transport.requests",
    "google.oauth2", "google.oauth2.service_account",
    "supabase", "gotrue", "jwt",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Provide the minimal stubs chatbot.rag expects
sys.modules["supabase"].create_client = MagicMock()
sys.modules["supabase"].Client = MagicMock()
