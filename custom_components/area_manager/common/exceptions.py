class SystemAttributeError(Exception):
    def __init__(self, key: str):
        self.error = f"Failed to modify attribute '{key}', Error: used by the system"
