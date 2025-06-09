from __future__ import annotations

import contextlib
from abc import ABC, ABCMeta, abstractmethod
from datetime import date
from typing import TYPE_CHECKING, Iterator, TypeVar
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

from .common import xml_to_dict
from .session import session

if TYPE_CHECKING:  # pragma: no cover
    from datetime import datetime

_T = TypeVar("_T")


class _SmartschoolXMLMeta(ABCMeta):
    """
    The metaclass will ONLY create this cache dictionary ones per class instantiation.

    Effectively giving each derived class I make their own dictionary.
    """

    def __new__(cls, name, bases, dct):
        dct["cache"] = {}
        return super().__new__(cls, name, bases, dct)


class SmartschoolXML(ABC, metaclass=_SmartschoolXMLMeta):
    cache: dict  # Type hint for the dynamically added attribute

    def _construct_command(self) -> str:
        txt = "<request><command>"
        txt += f"<subsystem>{self._subsystem}</subsystem>"
        txt += f"<action>{self._action}</action>"
        txt += "<params>"

        for k, v in self._params.items():
            txt += f"<param name={quoteattr(k)}><![CDATA[{v}]]></param>"

        txt += "</params></command></request>"
        return txt

    def __iter__(self) -> Iterator[_T]:
        yield from self._xml()

    def get(self) -> _T:
        """
        Retrieve only the first entry.

        This is particularly useful when you want to fetch just one entry, and don't want to use the `list(Class())[0]` syntax.
        Instead, you can use `Class().get()`.
        """
        return next(iter(self))

    @abstractmethod
    def _get_from_cache(self) -> object:
        """
        Retrieves information from the cache.

        Throws a `KeyError` when not found.
        """

    @abstractmethod
    def _store_into_cache(self, obj: object) -> None:
        """Stores the current value into the cache."""

    @property
    @abstractmethod
    def _url(self) -> str:
        """The URL where the data should be posted to."""

    def _xml(self):
        with contextlib.suppress(KeyError):
            return self._get_from_cache()
        
        # print(f"Request: {self._url} : {self._construct_command()}")
        response = session.post(
            self._url,
            data={
                "command": self._construct_command(),
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        # print(f"Response: {response.text}")

        root = ET.fromstring(response.text)

        all_entries = []
        as_obj = self._object_to_instantiate
        for el in root.findall(self._xpath):
            as_dict = xml_to_dict(el)
            self._post_process_element(as_dict)
            obj = as_obj(**as_dict)
            all_entries.append(obj)

        self._store_into_cache(all_entries)

        return all_entries

    @property
    @abstractmethod
    def _subsystem(self) -> str:
        """Returns the subsystem to request the info from."""

    @property
    @abstractmethod
    def _action(self) -> str:
        """Returns the action to send."""

    @property
    @abstractmethod
    def _params(self) -> dict:
        """Returns the parameters to send."""

    @property
    @abstractmethod
    def _xpath(self) -> str:
        """Returns the xpath to investigate."""

    @property
    @abstractmethod
    def _object_to_instantiate(self) -> type[_T]:
        """Returns the object to instantiate."""

    def _post_process_element(self, element: dict) -> None:
        """By default, this doesn't do anything, but you can adjust the parsed XML when needed."""


class SmartschoolXML_WeeklyCache(SmartschoolXML, ABC):
    @property
    def _cache_key(self):
        # Week number
        today = self.timestamp_to_use or date.today()
        return today.strftime("%Y-%U")

    def _get_from_cache(self) -> object:
        return self.cache[self._cache_key]

    def _store_into_cache(self, obj: object) -> None:
        self.cache[self._cache_key] = obj

    def __init__(self, timestamp_to_use: datetime | None = None):
        self.timestamp_to_use = timestamp_to_use


class SmartschoolXML_NoCache(SmartschoolXML, ABC):
    def _get_from_cache(self) -> object:
        raise KeyError

    def _store_into_cache(self, _: object) -> None:
        return
