import os
import sys
from pathlib import Path

os.environ["USERS"] = "tester:pass123"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["INSECURE_COOKIES"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
