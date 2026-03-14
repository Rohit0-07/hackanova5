"""Custom exception classes for the Research Paper Graph system."""


class CrawlSessionNotFoundError(Exception):
    """Raised when a crawl session ID is not found."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Crawl session '{session_id}' not found")


class PaperNotFoundError(Exception):
    """Raised when a paper ID is not found."""

    def __init__(self, paper_id: str):
        self.paper_id = paper_id
        super().__init__(f"Paper '{paper_id}' not found")


class SourceAPIError(Exception):
    """Raised when an external API call fails."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"Source API '{source}' error: {message}")
