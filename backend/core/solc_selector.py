"""
Automated solc compiler version detection and solc-select switcher.
Supports exact, caret, range, tilde pragma expressions, version normalization,
multi-file version resolution, and graceful fallback when solc-select is absent.
"""
import shutil
import subprocess
import re
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Union

logger = logging.getLogger("SolcSelector")


class SolcSelector:
    """Detects required Solidity compiler version from pragma and switches solc-select."""

    # Matches pragma solidity <expression>;
    PRAGMA_STATEMENT_REGEX = re.compile(r"pragma\s+solidity\s+([^;]+);", re.IGNORECASE)

    # Version pattern: captures x.y.z or x.y
    SEMVER_REGEX = re.compile(r"([0-9]+)\.([0-9]+)(?:\.([0-9]+))?")

    @classmethod
    def is_solc_select_available(cls) -> bool:
        """Returns True if the solc-select CLI is installed in PATH."""
        return shutil.which("solc-select") is not None

    @classmethod
    def normalize_version(cls, version_str: str) -> str:
        """
        Normalizes compiler release strings to clean semver format (x.y.z).
        Example: 'v0.8.20+commit.a1b2c3d4' -> '0.8.20'
        """
        if not version_str or not isinstance(version_str, str):
            return "0.8.20"

        clean = version_str.strip().lstrip("vV")
        # Remove commit hash suffixes like '+commit.12345'
        if "+" in clean:
            clean = clean.split("+")[0]

        match = cls.SEMVER_REGEX.search(clean)
        if match:
            major = match.group(1)
            minor = match.group(2)
            patch = match.group(3) if match.group(3) is not None else "0"
            return f"{major}.{minor}.{patch}"

        return clean

    @classmethod
    def parse_version_tuple(cls, version_str: str) -> Tuple[int, int, int]:
        """Parses a version string into an integer tuple (major, minor, patch)."""
        norm = cls.normalize_version(version_str)
        parts = norm.split(".")
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except ValueError:
            return (0, 0, 0)

    @classmethod
    def detect_version(cls, source_or_file: Union[str, Path]) -> Optional[str]:
        """
        Detects Solidity compiler version from source string or file path.
        Handles ^0.8.20, >=0.7.0 <0.9.0, ~0.8.4, and exact versions.
        """
        content = ""
        try:
            path = Path(source_or_file)
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8")
            else:
                content = str(source_or_file)
        except Exception:
            content = str(source_or_file)

        if not content:
            return None

        match = cls.PRAGMA_STATEMENT_REGEX.search(content)
        if not match:
            # Fallback: search for direct version regex if no full pragma statement found
            direct_match = re.search(r"pragma\s+solidity\s+[\^~>=<\s]*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", content)
            if direct_match:
                return cls.normalize_version(direct_match.group(1))
            return None

        expr = match.group(1).strip()

        # Find all semver tokens in the pragma expression
        ver_matches = cls.SEMVER_REGEX.findall(expr)
        if not ver_matches:
            return None

        # Convert matches to normalized strings
        versions = [f"{m[0]}.{m[1]}.{m[2] if m[2] else '0'}" for m in ver_matches]

        # For range pragmas like >=0.7.6 <0.9.0, or caret ^0.8.20:
        # Return the first explicit lower bound / version token
        return versions[0]

    @classmethod
    def resolve_best_version(cls, versions: List[str]) -> Optional[str]:
        """
        Given a list of candidate solc versions from multiple files,
        determines the highest compatible version.
        """
        valid_versions = [v for v in versions if v and v != "unknown"]
        if not valid_versions:
            return None

        # Sort by semver tuple
        sorted_versions = sorted(valid_versions, key=cls.parse_version_tuple, reverse=True)
        return cls.normalize_version(sorted_versions[0])

    @classmethod
    def switch_version(cls, version: str) -> bool:
        """
        Switches active Solidity compiler version via solc-select.
        Returns False gracefully if solc-select is not installed.
        """
        if not cls.is_solc_select_available():
            logger.debug("solc-select is not installed on system. Skipping compiler switch.")
            return False

        clean_version = cls.normalize_version(version)
        try:
            # Install if missing, then switch
            subprocess.run(
                ["solc-select", "install", clean_version],
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )
            proc = subprocess.run(
                ["solc-select", "use", clean_version],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            if proc.returncode == 0:
                logger.info(f"Switched solc compiler version to {clean_version}")
                return True
        except Exception as e:
            logger.warning(f"Failed to switch solc version via solc-select: {e}")
        return False
