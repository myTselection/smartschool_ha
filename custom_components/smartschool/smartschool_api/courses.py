from __future__ import annotations

from datetime import datetime # Keep datetime for parsing
from functools import cached_property
import logging
import re
from typing import Iterator # Removed Union, Literal

from bs4 import BeautifulSoup, Tag
# Removed Pydantic imports as models are now external
# from pydantic import BaseModel, Field, computed_field

from .objects import Course, CourseCondensed
from .session import session
from .exceptions import SmartSchoolException, SmartSchoolParsingError, SmartSchoolDownloadError
# Import the models from objects.py now
from .objects import FileItem, FolderItem, DocumentOrFolderItem


# Removed DocumentItemBase, FolderItem, FileItem, DocumentOrFolderItem definitions

__all__ = ["Courses", "TopNavCourses", "CourseDocuments"] # Removed model names from __all__

# Setup logger for this module
logger = logging.getLogger(__name__)


class TopNavCourses:
    """
    Retrieves a list of the courses which are available from the top navigation bar.

    This structure is different from the `Courses` results.

    Example:
    -------
    >>> for course in TopNavCourses():
    >>>     print(course.name)
    Aardrijkskunde_3_LOP_2023-2024
    bibliotheek

    """

    @cached_property
    def _list(self) -> list[CourseCondensed]:
        return [CourseCondensed(**course) for course in session.json("/Topnav/getCourseConfig", method="post")["own"]]

    def __iter__(self) -> Iterator[CourseCondensed]:
        yield from self._list


class Courses:
    """
    Retrieves a list of the courses.

    This structure is different from the `TopNavCourses` results.

    To reproduce: go to "Results", one of the XHR calls is this one

    Example:
    -------
    >>> for course in Courses():
    >>>     print(course.name)
    Aardrijkskunde
    Biologie

    """

    @cached_property
    def _list(self) -> list[Course]:
        return [Course(**course) for course in session.json("/results/api/v1/courses/")]

    def __iter__(self) -> Iterator[Course]:
        yield from self._list


class CourseDocuments:
    """
    Fetches the HTML representation of the document folder structure for a specific course
    and provides methods to parse and list its contents.

    Requires a course ID to initialize. The `get_folder_html` method can optionally
    take a folder ID (`ssID`) to fetch a specific subfolder's structure.
    The `list_folder_contents` method parses this HTML to return a list of files and folders.

    Example:
    -------
    >>> course_docs = CourseDocuments(course_id=4128)
    >>> root_html = course_docs.get_folder_html() # Get root folder HTML
    >>> subfolder_html = course_docs.get_folder_html(folder_id=65) # Get specific folder HTML
    >>> items = course_docs.list_folder_contents(folder_id=65) # List contents of specific folder
    >>> for item in items:
    >>>     print(f"{item.type}: {item.name}")
    """
    def __init__(self, course_id: int):
        if not isinstance(course_id, int) or course_id <= 0:
            raise ValueError("course_id must be a positive integer.")
        self.course_id = course_id
        self._base_path = f"/Documents/Index/Index/courseID/{self.course_id}"

    def get_folder_html(self, folder_id: int | None = None) -> str:
        """
        Fetches the HTML content for a specific folder within the course documents.

        Args:
            folder_id: The specific folder ID (`ssID`) to fetch. If None, fetches the
                       root document folder for the course.

        Returns:
            The raw HTML content of the folder page as a string.

        Raises:
            SmartSchoolException: If the request fails or returns an error status.
        """
        target_path = self._base_path
        if folder_id is not None:
            if not isinstance(folder_id, int) or folder_id <= 0:
                raise ValueError("folder_id must be a positive integer if provided.")
            target_path += f"/ssID/{folder_id}"

        # Define headers - minimal set, session handles cookies
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": session.create_url("/") # Referer might be important
        }

        try:
            response = session.get(target_path, headers=headers)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.text
        except Exception as e:
            # Wrap specific request errors or re-raise generic ones
            raise SmartSchoolException(f"Failed to fetch document folder HTML for course {self.course_id}, folder {folder_id}: {e}") from e # Corrected casing

    def list_folder_contents(self, folder_id: int | None = None) -> list[DocumentOrFolderItem]:
        """
        Parses the HTML of a course document folder (table view, e.g., id='doclist')
        and returns a list of its contents using models from file_fetch.py.

        Args:
            folder_id: The specific folder ID (`ssID`) to list contents for. If None,
                       lists the contents of the root document folder for the course.

        Returns:
            A list of FolderItem and FileItem objects (defined in file_fetch.py).

        Raises:
            SmartSchoolParsingError: If the HTML structure cannot be parsed as expected.
        """
        html_content = self.get_folder_html(folder_id)
        soup = BeautifulSoup(html_content, 'html.parser')

        items: list[DocumentOrFolderItem] = []
        # The `parent_id` for items *inside* this folder is `folder_id`.
        # If folder_id is None (root), parent_id is likely 0.
        containing_folder_id = folder_id if folder_id is not None else 0 # Assuming 0 for root's parent

        doc_table = soup.find('table', id='doclist')
        if not doc_table or not isinstance(doc_table, Tag):
            logger.warning(f"Could not find table#doclist in course {self.course_id}, folder {folder_id}. This view might use divs (try file_fetch.browse_course_documents) or the structure changed.")
            return []

        tbody = doc_table.find('tbody')
        if not tbody or not isinstance(tbody, Tag):
             logger.warning(f"Could not find tbody within table#doclist for course {self.course_id}, folder {folder_id}.")
             return []

        rows = tbody.find_all('tr', recursive=False)

        for row in rows:
            if not isinstance(row, Tag): continue
            cells = row.find_all('td', recursive=False)
            if len(cells) < 5:
                logger.debug(f"Skipping row with insufficient cells ({len(cells)}): {row.prettify()}")
                continue

            name_cell = cells[1]
            link = name_cell.find('a', href=True)
            if not link or not isinstance(link, Tag):
                logger.debug(f"Skipping row without a valid link in the name cell: {row.prettify()}")
                continue

            href = link['href']
            name = link.get_text(strip=True)
            if not name:
                 logger.debug(f"Skipping row with empty name: {row.prettify()}")
                 continue

            description = cells[2].get_text(strip=True) if len(cells) > 2 else None
            size_str = cells[3].get_text(strip=True) if len(cells) > 3 else None
            date_str = cells[4].get_text(strip=True) if len(cells) > 4 else None

            size_kb = None
            if size_str:
                size_match = re.search(r'([\d,.]+)\s*(KB|MB|GB)', size_str, re.IGNORECASE)
                if size_match:
                    try:
                        value = float(size_match.group(1).replace(',', '.'))
                        unit = size_match.group(2).upper()
                        if unit == 'MB': value *= 1024
                        elif unit == 'GB': value *= 1024 * 1024
                        size_kb = value
                    except ValueError:
                        logger.warning(f"Could not parse size value: {size_match.group(1)}")
                elif size_str.strip() and size_str.strip() != '-':
                    logger.warning(f"Could not parse size string format: {size_str}")

            last_modified = None
            if date_str:
                try:
                    last_modified = datetime.strptime(date_str, '%d.%m.%Y %H:%M')
                except ValueError:
                     try: # Try another common format
                         last_modified = datetime.strptime(date_str, '%d-%m-%Y %H:%M')
                     except ValueError:
                        logger.warning(f"Could not parse date string format: {date_str}")


            try:
                is_folder = link.find('i', class_='fa-folder') is not None or '/Documents/Index/Index/' in href
                folder_match = re.search(r'/ssID/(\d+)', href) # ssID is the folder's own ID
                file_match = re.search(r'/docID/(\d+)', href) # docID is the file's own ID

                if is_folder and folder_match:
                    item_id = int(folder_match.group(1)) # This is the ssID of the folder item
                    item = FolderItem(
                        name=name,
                        ss_id=item_id, # Use ss_id field from file_fetch model
                        parent_id=containing_folder_id, # The ID of the folder we are currently listing
                        description=description,
                        # browse_url=href # file_fetch model doesn't have browse_url
                        # course_id=self.course_id # file_fetch model doesn't have course_id directly
                    )
                    items.append(item)
                elif file_match: # Assume file if docID is present
                    item_id = int(file_match.group(1)) # This is the docID of the file item
                    # Determine download path vs view url
                    download_path = href if '/Documents/Download/download/' in href else None
                    # view_url = href if 'Wopi' in href else None # file_fetch model doesn't have view_url

                    # Extract mime type from icon class if possible
                    mime_type = None
                    icon = link.find('i', class_=re.compile(r'fa-file-'))
                    if icon:
                        icon_class = next((cls for cls in icon.get('class', []) if cls.startswith('fa-file-')), None)
                        if icon_class:
                            # Basic mapping (keep consistent with file_fetch if possible)
                            if 'pdf' in icon_class: mime_type = 'application/pdf'
                            elif 'word' in icon_class: mime_type = 'application/msword' # Or vnd.openxmlformats-officedocument.wordprocessingml.document
                            elif 'excel' in icon_class: mime_type = 'application/vnd.ms-excel' # Or vnd.openxmlformats-officedocument.spreadsheetml.sheet
                            elif 'powerpoint' in icon_class: mime_type = 'application/vnd.ms-powerpoint' # Or vnd.openxmlformats-officedocument.presentationml.presentation
                            elif 'image' in icon_class: mime_type = 'image/*'
                            elif 'archive' in icon_class: mime_type = 'application/zip'
                            elif 'text' in icon_class: mime_type = 'text/plain'

                    item = FileItem(
                        name=name,
                        doc_id=item_id, # Use doc_id field from file_fetch model
                        parent_id=containing_folder_id, # The ID of the folder we are currently listing
                        description=description,
                        download_url_path=download_path, # Use download_url_path field
                        mime_type=mime_type, # Use mime_type field
                        size_kb=size_kb, # Use size_kb field
                        last_modified=last_modified, # Use last_modified field
                        # course_id=self.course_id # file_fetch model doesn't have course_id directly
                    )
                    items.append(item)
                else:
                    logger.warning(f"Could not determine type or extract ID for item '{name}' with href '{href}' in course {self.course_id}, folder {folder_id}.")

            except (AttributeError, ValueError, IndexError, TypeError) as e:
                logger.error(f"Error parsing row in course {self.course_id}, folder {folder_id}: {e}\nRow HTML: {row.prettify()}", exc_info=True)
                continue

        return items
