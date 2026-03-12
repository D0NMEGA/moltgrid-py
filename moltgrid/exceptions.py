class MoltGridError(Exception):
    """Raised when the MoltGrid API returns a 4xx/5xx response."""

    def __init__(self, status_code, detail, response=None):
        self.status_code = status_code
        self.detail = detail
        self.response = response
        super().__init__(f"MoltGrid API error {status_code}: {detail}")
