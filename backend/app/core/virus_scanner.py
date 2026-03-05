"""
FakeBuster AI — ClamAV Virus Scanner Integration
Scans uploaded files via ClamAV TCP daemon before processing.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import clamd

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScanStatus(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


@dataclass
class ScanResult:
    status: ScanStatus
    detail: str = ""


class VirusScanner:
    """ClamAV scanner client connecting via TCP socket."""

    def __init__(self):
        self._client: clamd.ClamdNetworkSocket | None = None

    def connect(self) -> bool:
        """Establish connection to ClamAV daemon."""
        try:
            self._client = clamd.ClamdNetworkSocket(
                host=settings.CLAMAV_HOST,
                port=settings.CLAMAV_PORT,
                timeout=30,
            )
            self._client.ping()
            logger.info("ClamAV connection established")
            return True
        except Exception as e:
            logger.warning(f"ClamAV connection failed: {e}")
            self._client = None
            return False

    def is_available(self) -> bool:
        """Check if ClamAV daemon is reachable."""
        if self._client is None:
            return self.connect()
        try:
            self._client.ping()
            return True
        except Exception:
            return self.connect()

    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan a file for malware.
        Returns ScanResult with status and detail.
        """
        if not self.is_available():
            logger.warning("ClamAV not available — skipping scan")
            return ScanResult(
                status=ScanStatus.ERROR,
                detail="Virus scanner unavailable",
            )

        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return ScanResult(
                    status=ScanStatus.ERROR,
                    detail=f"File not found: {file_path}",
                )

            result = self._client.scan(str(path))

            if result is None:
                return ScanResult(status=ScanStatus.CLEAN)

            # ClamAV returns {filepath: ('status', 'signature')}
            file_result = result.get(str(path))
            if file_result is None:
                return ScanResult(status=ScanStatus.CLEAN)

            status_str, signature = file_result
            if status_str == "OK":
                return ScanResult(status=ScanStatus.CLEAN)
            elif status_str == "FOUND":
                logger.warning(f"MALWARE DETECTED in {file_path}: {signature}")
                return ScanResult(
                    status=ScanStatus.INFECTED,
                    detail=f"Malware detected: {signature}",
                )
            else:
                return ScanResult(
                    status=ScanStatus.ERROR,
                    detail=f"Unexpected scan result: {status_str}",
                )

        except Exception as e:
            logger.error(f"ClamAV scan error for {file_path}: {e}")
            return ScanResult(
                status=ScanStatus.ERROR,
                detail=f"Scan error: {str(e)}",
            )


# Module-level singleton
virus_scanner = VirusScanner()
