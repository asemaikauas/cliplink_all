"""Custom exceptions for the ClipLink application."""

from typing import Optional


class SubtitleError(Exception):
    """Base exception for subtitle-related errors."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.task_id = task_id


class TranscriptionError(SubtitleError):
    """Raised when audio transcription fails."""
    pass


class SubtitleFormatError(SubtitleError):
    """Raised when subtitle format conversion fails."""
    pass


class BurnInError(SubtitleError):
    """Raised when subtitle burn-in process fails."""
    pass


class VADError(SubtitleError):
    """Raised when Voice Activity Detection fails."""
    pass


class FileUploadError(Exception):
    """Raised when file upload to Azure Blob Storage fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.file_path = file_path


class FileDownloadError(Exception):
    """Raised when file download from Azure Blob Storage fails."""
    
    def __init__(self, message: str, blob_url: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.blob_url = blob_url 