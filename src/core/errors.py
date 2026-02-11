class ConfigError(Exception):
    pass


class RegisterError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


class ScriptError(Exception):
    pass
