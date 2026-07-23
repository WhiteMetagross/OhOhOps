import asyncio
from app.services.sandbox import execute_in_sandbox

async def main():
    # A simple script that prints to stdout and exits cleanly
    code = "print('Hello from the secure Docker sandbox!')\n"
    
    print("Dispatching test code to Docker sandbox...\n")
    exit_code, stdout, stderr = await execute_in_sandbox(code)
    
    print(f"OK: Exit code: {exit_code}")
    print(f"Stdout: {stdout.strip()}")
    
    if stderr:
        print(f"WARNING: Stderr: {stderr.strip()}")
        
    if exit_code == 0 and "Hello from the secure Docker sandbox!" in stdout:
        print("\nSandbox is working flawlessly!")
    else:
        print("\nERROR: Sandbox failed. Confirm Docker is running and the configured sandbox image is available.")

if __name__ == "__main__":
    asyncio.run(main())
