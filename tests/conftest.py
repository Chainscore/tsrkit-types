import sys, pathlib, os

# Ensure the project root directory is in sys.path so that the tsrkit_types
# package (which lives at the repository root) can be imported when the test
# runner's working directory is the tests/ folder.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))