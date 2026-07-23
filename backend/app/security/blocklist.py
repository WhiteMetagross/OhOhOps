import re
from typing import Tuple

# Absolute blocklist of destructive or unauthorized Python commands.
# This prevents the AI from running anything obviously malicious in the sandbox.
DANGEROUS_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.",
    r"os\.remove\s*\(",
    r"os\.rmdir\s*\(",
    r"shutil\.rmtree\s*\(",
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"os\.environ",          # prevent credential dumping
    r"open\s*\(\s*['\"]/etc", # prevent access to system files
    r"requests\.post",       # prevent basic network exfiltration
    r"urllib\.request",
]

# Compile into a single regex for O(n) scanning
BLOCKLIST_REGEX = re.compile("|".join(DANGEROUS_PATTERNS))

def check_blocklist(code: str) -> Tuple[bool, str]:
    """
    Scans the Python code against a regex blocklist of destructive commands.
    Returns (is_safe, reason).
    """
    match = BLOCKLIST_REGEX.search(code)
    if match:
        return False, f"Static analysis blocked execution due to forbidden pattern: {match.group(0)}"
        
    return True, ""
