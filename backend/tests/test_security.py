import pytest
from app.security.blocklist import check_blocklist

def test_blocklist_catches_rm_rf():
    unsafe_code = "import os\nos.system('rm -rf /')"
    is_safe, reason = check_blocklist(unsafe_code)
    assert not is_safe
    assert "destructive or unauthorized" in reason.lower() or "blocked" in reason.lower() or "rm" in reason.lower()

def test_blocklist_allows_safe_code():
    safe_code = "import math\nprint(math.sqrt(4))"
    is_safe, reason = check_blocklist(safe_code)
    assert is_safe
