from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Union

from bs4 import BeautifulSoup

from .exceptions import SmartSchoolAuthenticationError, SmartSchoolException
# Import models from objects.py
from .objects import FileItem, FolderItem, DocumentOrFolderItem
from .session import session

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)

__all__ = ["download_document", "browse_course_documents"]


def _parse_size_kb(size_str: str) -> float:
    """Parses size string like '482.13 KiB' into float KB."""
    match = re.match(r"([\d.]+)\s*KiB", size_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    logger.warning(f"Could not parse size string: {size_str}")
    return 0.0

def _parse_datetime(datetime_str: str) -> datetime | None:
    """Parses datetime string like '2025-01-14 11:53'."""
    try:
        # Assuming local timezone if none is provided by SmartSchool
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        logger.warning(f"Could not parse datetime string: {datetime_str}")
        return None


def browse_course_documents(
    course_id: int,
    folder_id: int,
    ss_id: int,
) -> List[DocumentOrFolderItem]: # Updated return type hint
    """
    Browses the contents (files and subfolders) of a specific folder
    within a course's document section.

    Args:
        course_id: The ID of the course.
        folder_id: The ID of the folder (parentID) to browse. Use 0 for the root folder.
        ss_id: The session/school ID (ssID) required in the URL.

    Returns:
        A list containing FileItem and FolderItem objects representing the
        contents of the folder.

    Raises:
        SmartSchoolException: If fetching or parsing the folder page fails.
        SmartSchoolAuthenticationError: If redirected to the login page.
    """
    browse_url_path = f"/Documents/Index/Index/courseID/{course_id}/parentID/{folder_id}/ssID/{ss_id}"
    full_browse_url = session.create_url(browse_url_path)

    logger.info(f"Browsing course documents for courseID={course_id}, folderID={folder_id}")

    try:
        response = session.get(full_browse_url, allow_redirects=True)
        response.raise_for_status()

        if "/login" in response.url:
            raise SmartSchoolAuthenticationError(f"Redirected to login page when browsing folderID {folder_id}. Session might be invalid.")

        soup = BeautifulSoup(response.content, 'html.parser')
        items: List[DocumentOrFolderItem] = [] # Updated list type hint

        # Find all rows representing files or folders
        rows = soup.select("div.smsc_cm_body_row")

        for row in rows:
            doc_id_str = row.get('id')
            if not doc_id_str or not doc_id_str.startswith("docID_"):
                continue
            try:
                item_id = int(doc_id_str.split('_')[1])
            except (IndexError, ValueError):
                logger.warning(f"Could not parse item ID from: {doc_id_str}")
                continue

            name_div = row.select_one("div.name")
            link_tag = name_div.select_one("a.smsc_cm_link") if name_div else None
            if not link_tag:
                # Some items might not have a direct link (e.g., older files?)
                # Try to get the name from the div directly if possible
                name = name_div.get_text(strip=True) if name_div else f"Unknown Item {item_id}"
                logger.warning(f"Could not find link tag for item {item_id}, using name: {name}")
                # Decide how to handle items without links - skip or create a basic entry?
                # Skipping for now as their type is uncertain.
                continue

            name = link_tag.get_text(strip=True)
            href = link_tag.get('href')
            description_div = row.select_one("div.smsc_cm_body_row_block_desc")
            description = description_div.get_text(strip=True) if description_div else None

            style_attr = row.select_one("div.smsc_cm_body_row_block").get('style', '')
            is_folder = 'mime_folder' in style_attr

            if is_folder:
                # Extract ssID for the folder from its browse link
                folder_ss_id_match = re.search(r'/ssID/(\d+)', href)
                item_ss_id = int(folder_ss_id_match.group(1)) if folder_ss_id_match else item_id # Fallback? ssID is usually in the link

                items.append(FolderItem(
                    id=item_ss_id, # Use extracted ssID as the folder's ID
                    name=name,
                    description=description,
                    browse_url=href # The href for folders is the browse URL
                ))
            else:
                # It's a file
                mime_div = row.select_one("div.smsc_cm_body_row_block_mime")
                mime_text = mime_div.get_text(strip=True) if mime_div else ""
                parts = mime_text.split(' - ')
                mime_type = parts[0] if parts else "Unknown"
                size_kb = _parse_size_kb(parts[1]) if len(parts) > 1 else 0.0
                last_modified_dt = _parse_datetime(parts[2]) if len(parts) > 2 else None

                # Construct download URL (similar to download_document)
                # Note: The view_url might be the primary link for WOPI-enabled files
                view_url = href if 'Wopi' in href else None
                # Basic download URL structure assumption
                download_url_path = f"/Documents/Download/download/courseID/{course_id}/docID/{item_id}/ssID/{ss_id}" # More standard download path

                items.append(FileItem(
                    id=item_id, # This is docID for files
                    name=name,
                    description=description,
                    mime_type=mime_type,
                    size_kb=size_kb,
                    last_modified=last_modified_dt,
                    download_url=download_url_path, # Pass the relative path
                    view_url=view_url # Use the href if it's a WOPI link
                ))

        logger.info(f"Found {len(items)} items in folderID={folder_id}")
        return items

    except Exception as e:
        raise SmartSchoolException(f"Failed to browse documents for courseID={course_id}, folderID={folder_id}: {e}") from e


def download_document(
    course_id: int,
    doc_id: int,
    ss_id: int,
    target_path: str | Path,
    overwrite: bool = False
) -> Path:
    """
    Downloads a specific document from a course's document section.

    Args:
        course_id: The ID of the course containing the document.
        doc_id: The ID of the document (docID) to download.
        ss_id: The ID of the folder (ssID) containing the document.
        target_path: The local file path (including filename) where the document
                     should be saved. If it's a directory, the original filename
                     might be inferred from headers (if available) or a default used.
        overwrite: If True, overwrite the target file if it already exists.
                   Defaults to False.

    Returns:
        The Path object representing the downloaded file.

    Raises:
        SmartSchoolException: If the download fails, the target path is invalid,
                              or the file exists and overwrite is False.
        FileNotFoundError: If the target directory does not exist.
    """
    # Construct the download URL
    # This assumes the download URL format is consistent.
    # If FileItem provides a reliable download_url, prefer using that.
    download_url_path = f"/Documents/Download/Index/htm/0/courseID/{course_id}/docID/{doc_id}/ssID/{ss_id}"
    full_download_url = session.create_url(download_url_path)

    target_filepath = Path(target_path)

    # Ensure target directory exists
    if not target_filepath.parent.exists():
        raise FileNotFoundError(f"Target directory does not exist: {target_filepath.parent}")
    if target_filepath.is_dir():
         # If target is a directory, raise error as we can't reliably get filename yet.
         raise ValueError("target_path must be a full file path, not a directory.")

    # Check for existing file
    if target_filepath.exists() and not overwrite:
        raise SmartSchoolException(f"Target file already exists and overwrite is False: {target_filepath}")

    logger.info(f"Attempting to download document docID={doc_id} from courseID={course_id} to {target_filepath}")

    try:
        # Use stream=True for potentially large files
        with session.get(full_download_url, stream=True, allow_redirects=True) as response:
            response.raise_for_status() # Check for HTTP errors

            # Check if we were redirected to login
            if "/login" in response.url:
                 raise SmartSchoolAuthenticationError(f"Redirected to login page when downloading docID {doc_id}. Session might be invalid.")

            # Write the content to the file
            with open(target_filepath, 'wb') as f:
                shutil.copyfileobj(response.raw, f)

            logger.info(f"Successfully downloaded document to {target_filepath}")
            return target_filepath

    except Exception as e:
        # Clean up potentially partially downloaded file on error
        if target_filepath.exists():
            try:
                target_filepath.unlink()
            except OSError:
                logger.warning(f"Could not remove partially downloaded file: {target_filepath}")
        raise SmartSchoolException(f"Failed to download document docID={doc_id} from {full_download_url}: {e}") from e
