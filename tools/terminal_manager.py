import subprocess
import threading
import queue
import time
import os
import signal

class TerminalManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TerminalManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized: return
        self.process = subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoExit", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP # Important for Ctrl+C on Windows
        )
        self.output_queue = queue.Queue()
        self.history = []
        self.is_executing = False
        self.current_marker = ""
        
        # Reader thread
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        self.initialized = True

    def _read_output(self):
        while True:
            line = self.process.stdout.readline()
            if not line: break
            self.output_queue.put(line)
            self.history.append(line)
            if len(self.history) > 1000:
                self.history.pop(0)

    def execute_stream(self, cmd):
        """Executes a command and yields output line by line."""
        self.is_executing = True
        self.current_marker = f"____DONE_{int(time.time())}____"
        
        # We use a marker to know when the command is truly finished
        # Note: We use Write-Host to avoid it being captured by some tools but seen by us
        full_cmd = f"{cmd}\nWrite-Host '{self.current_marker}'\n"
        
        try:
            self.process.stdin.write(full_cmd)
            self.process.stdin.flush()
        except Exception as e:
            yield f"Error sending to PowerShell: {e}\n"
            self.is_executing = False
            return

        command_output = ""
        while self.is_executing:
            try:
                line = self.output_queue.get(timeout=0.1)
                if self.current_marker in line:
                    self.is_executing = False
                    break
                command_output += line
                yield line
            except queue.Empty:
                if self.process.poll() is not None:
                    yield "PowerShell process terminated unexpectedly.\n"
                    self.is_executing = False
                    break
                continue
        
        self.is_executing = False

    def interrupt(self):
        """Sends Ctrl+C to the PowerShell process group."""
        if self.process and self.process.poll() is None:
            # On Windows, we send CTRL_BREAK or CTRL_C to the process group
            self.process.send_signal(signal.CTRL_BREAK_EVENT)
            return True
        return False

    def terminate(self):
        """Force kills the PowerShell process."""
        if self.process:
            self.process.terminate()
            self.process.wait()

# Singleton instance
terminal_manager = TerminalManager()
