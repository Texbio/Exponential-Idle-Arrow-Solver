import uvicorn
import os
import time
import subprocess
import sys


def start_server(host="127.0.0.1", port=8000, app_module="solver_backend:app"):
    """Starts the Uvicorn server in a non-blocking subprocess."""
    # This command ensures that the subprocess runs the uvicorn module
    # using the same python executable that is running this script.
    command = [
        sys.executable,
        "-m", "uvicorn",
        app_module,
        "--host", host,
        "--port", str(port)
    ]
    print(f"Executing command: {' '.join(command)}")
    return subprocess.Popen(command)


def stop_server(process):
    """Stops a running server process gracefully."""
    if process.poll() is None:  # Check if the process is still running
        print("Stopping server...")
        process.terminate()
        try:
            # Wait for the process to terminate
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop
            print("Server did not stop gracefully, forcing termination.")
            process.kill()
        print("Server stopped.")
    else:
        print("Server process already terminated.")


if __name__ == "__main__":
    """
    This script provides a more controlled way to run and reload the FastAPI server.

    It manually checks the 'solver_backend.py' file's modification time
    every second for changes. This is more reliable than checking file size.

    It only prints output when a change is detected, providing cleaner
    feedback during development.
    """
    app_module_str = "solver_backend:app"
    file_to_watch = "solver_backend.py"

    # Ensure the file to watch actually exists before starting
    if not os.path.exists(file_to_watch):
        print(f"Error: File '{file_to_watch}' not found. Cannot start watcher.")
        sys.exit(1)

    # Use the file's last modification time for change detection (more reliable)
    last_mod_time = os.path.getmtime(file_to_watch)
    server_process = None

    try:
        print(f"Starting server for: {app_module_str}")
        server_process = start_server()
        print(f"Watching '{file_to_watch}' for modification changes... (Press Ctrl+C to stop)")

        while True:
            time.sleep(2)  # Check every 1 second

            # Check if the file's modification time has changed
            try:
                current_mod_time = os.path.getmtime(file_to_watch)
            except FileNotFoundError:
                print(f"\nError: '{file_to_watch}' has been deleted. Stopping.")
                break

            if current_mod_time != last_mod_time:
                print(f"\n--- Change detected in '{file_to_watch}'. Reloading server... ---")
                last_mod_time = current_mod_time

                # Stop the old server and start a new one
                if server_process:
                    stop_server(server_process)

                server_process = start_server()
                print(f"Server reloaded. Watching for next change...")

    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        # Ensure the server is stopped when the script exits
        if server_process:
            stop_server(server_process)
        print("Script finished.")
