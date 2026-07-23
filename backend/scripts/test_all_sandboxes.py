"""Execute every supported language in the isolated Docker sandbox."""

from __future__ import annotations

import asyncio

from app.services.sandbox import execute_in_sandbox


CASES = {
    "main.py": ('print("python-ok")\n', "python-ok"),
    "main.js": ('console.log("javascript-ok");\n', "javascript-ok"),
    "main.ts": (
        'const value: number = 4;\nconsole.log("typescript-ok", value);\n',
        "typescript-ok 4",
    ),
    "main.c": (
        '#include <stdio.h>\nint main(void) { puts("c-ok"); return 0; }\n',
        "c-ok",
    ),
    "main.cpp": (
        '#include <iostream>\nint main() { std::cout << "cpp-ok\\n"; }\n',
        "cpp-ok",
    ),
    "main.go": (
        'package main\nimport "fmt"\nfunc main() { fmt.Println("go-ok") }\n',
        "go-ok",
    ),
}


async def main() -> None:
    for filename, (code, marker) in CASES.items():
        exit_code, stdout, stderr = await execute_in_sandbox(code, target_file=filename)
        assert exit_code == 0, f"{filename}: {stderr}"
        assert marker in stdout, f"{filename}: {stdout}"
        print(f"{filename}: passed")

    network_probe = """
import urllib.request
try:
    urllib.request.urlopen("https://example.com", timeout=2)
except Exception:
    print("network-blocked")
else:
    raise SystemExit("sandbox network was available")
"""
    exit_code, stdout, stderr = await execute_in_sandbox(
        network_probe,
        target_file="network_probe.py",
    )
    assert exit_code == 0, stderr
    assert "network-blocked" in stdout, stdout
    print("network isolation: passed")


if __name__ == "__main__":
    asyncio.run(main())
