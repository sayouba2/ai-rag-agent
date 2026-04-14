import os
import pytest

# Doit être défini AVANT tout import de app.*
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
