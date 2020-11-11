class ShellCommandException(Exception):
    def __init__(self, error: str, message: str, returncode: int):
        self.error = error
        self.message = message
        self.returncode = returncode
