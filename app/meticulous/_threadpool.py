"""
Multithread processing to maximize time value of user input
"""

import concurrent.futures

def fake():
    """
    Example task
    """
    return 5

def start_tasks(executor):
    """
    Add tasks to the executor until shutdown
    """
    yield executor.submit(fake)

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_iter = start_tasks(executor)
        for future in concurrent.futures.as_completed(future_iter):
            try:
                data = future.result()
            except Exception as exc:
                print(f"Error during task: {exc}")
            else:
                print(f"Output {data}")

if __name__ == '__main__':
    main()

