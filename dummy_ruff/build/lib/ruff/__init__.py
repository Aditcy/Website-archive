import subprocess

def run(*args, **kwargs):
    """Run the system-installed ruff CLI with given arguments, capturing output."""
    return subprocess.run(['ruff', 'check', *args], capture_output=True, text=True, **kwargs)
