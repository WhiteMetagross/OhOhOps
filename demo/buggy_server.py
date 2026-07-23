import sys
import time

def process_metrics():
    """
    Simulates a worker loop processing server metrics.
    Contains a deliberate bug: missing 'import math' but tries to use math.sqrt.
    """
    metrics = [10, 20, -5, 40]
    for m in metrics:
        if m < 0:
            # BUG: This will crash because 'math' is not imported!
            val = math.sqrt(abs(m))
            print(f"Processed absolute metric: {val}")
        else:
            print(f"Processed metric: {m}")
            
        time.sleep(0.5)

def main():
    print("Starting OhOhOps Demo Server...")
    try:
        process_metrics()
        print("Server running successfully!")
    except Exception as e:
        # We output the exact crash log so the SRE Agent can ingest it
        print(f"FATAL CRASH: {type(e).__name__}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
