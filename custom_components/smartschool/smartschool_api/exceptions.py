class SmartSchoolException(Exception):
    """Base exception class for smartschool API errors."""
    pass

class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""
    pass

class SmartSchoolParsingError(SmartSchoolException):
    """Indicates an error occurred while parsing data from Smartschool."""
    pass

class SmartSchoolDownloadError(SmartSchoolException):
    """Indicates an error occurred during a file download operation."""
    pass
