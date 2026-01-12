import os
import sys

# Ensure the repository root is on sys.path so `import app.*` works reliably
# across different pytest import modes/environments.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

