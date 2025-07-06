__all__ = ["SmartSchoolAuthenticationError", "SmartSchoolDownloadError", "SmartSchoolException", "SmartSchoolParsingError"]


class SmartSchoolException(Exception):
    """Base exception class for smartschool API errors."""


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""


class SmartSchoolParsingError(SmartSchoolException):
    """Indicates an error occurred while parsing data from Smartschool."""


class SmartSchoolDownloadError(SmartSchoolException):
    """Indicates an error occurred during a file download operation."""
