"""SolaX Cloud API."""

from asyncio import Lock, create_task, sleep
import logging

import httpx

_LOGGER = logging.getLogger(__name__)


class InvalidAPIToken(Exception):
    """An invalid API token was used."""


class InvalidDeviceSN(Exception):
    """An invalid device serial number was used."""


class ConnectionFailed(Exception):
    """The connection failed for another reason."""


class SolaXCloudAPI:
    """Class for accessing the SolaX Cloud API."""

    def __init__(self) -> None:
        """Initialise the SolaX Cloud API."""
        self._polling_task = None
        self._polling_lock = Lock()

    async def fetch_api_data(self, api_token: str, device_id: str):
        """Fetch data from the API."""
        await self._polling_lock.acquire()
        self._polling_task = create_task(self._polling_timeout())
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://eu.solaxcloud.com/proxyApp/proxy/api/getRealtimeInfo.do",
                    params={"tokenId": api_token, "sn": device_id},
                )
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"] is True:
                        return data["result"]
                    if data["code"] == 103:
                        raise InvalidAPIToken
                    if data["code"] == 0:
                        raise InvalidDeviceSN
                    raise ConnectionFailed
            except httpx.RequestError as err:
                _LOGGER.error(err)
                raise ConnectionFailed from err

    async def _polling_timeout(self) -> None:
        """Release the polling lock after the 10 second timeout."""
        await sleep(10)
        self._polling_task = None
        if self._polling_lock.locked():
            self._polling_lock.release()

    async def fetch_device_metadata(
        self: "SolaXCloudAPI", api_token: str, device_id: str
    ):
        """Fetch the device metadata."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://eu.solaxcloud.com/proxyApp/proxy/api/getRealtimeInfo.do",
                    params={"tokenId": api_token, "sn": device_id},
                )
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"] is True:
                        return {
                            "sn": device_id,
                            "inverterSN": data["result"]["inverterSN"],
                        }
                    if data["code"] == 103:
                        raise InvalidAPIToken
                    if data["code"] == 0:
                        raise InvalidDeviceSN
                    raise ConnectionFailed
            except httpx.RequestError as err:
                raise ConnectionFailed from err
