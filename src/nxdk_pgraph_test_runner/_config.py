# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import os
import shlex
import tomllib
from typing import Any

import tomli_w

logger = logging.getLogger(__name__)


class Config:
    """Holds program configuration information."""

    _DEFAULT_TIMEOUT_SECONDS = 120 * 60

    def __init__(
        self,
        work_dir: str | None = None,
        output_dir: str | None = None,
        emulator_command: str | None = None,
        iso_path: str | os.PathLike | None = None,
        ftp_ip: str | None = None,
        ftp_preferred_interface: str | None = None,
        ftp_ip_override: str | None = None,
        timeout_seconds: int = 0,
        xbox_artifact_path: str = "e:\nxdk_pgraph_tests",
        test_failure_retries: int = 1,
    ) -> None:
        self._emulator_command: str = emulator_command or ""
        self.iso_path: str = str(iso_path) if iso_path is not None else ""
        self.ftp_ip: str | None = ftp_ip
        self.ftp_preferred_interface: str | None = ftp_preferred_interface
        self.ftp_ip_override: str | None = ftp_ip_override
        self.timeout_seconds = timeout_seconds if timeout_seconds else self._DEFAULT_TIMEOUT_SECONDS
        self.xbox_artifact_path = xbox_artifact_path
        self.test_failure_retries = test_failure_retries

        self._provided_work_dir: str | None
        self._work_dir: str
        self._data_dir: str

        self._provided_output_dir: str | None
        self._output_dir: str

        self.set_work_dir(work_dir)
        self.set_output_dir(output_dir)

    def build_emulator_command(self, iso_path: str) -> list[str]:
        if not self._emulator_command:
            msg = "Emulator command was not provided."
            raise ValueError(msg)
        return shlex.split(self._emulator_command.replace("{ISO}", iso_path))

    def set_emulator_command(self, template: str):
        self._emulator_command = template

    def set_work_dir(self, work_dir: str | None):
        self._provided_work_dir = work_dir
        self._work_dir = work_dir if work_dir else os.path.abspath(".work")
        self._data_dir = os.path.join(self._work_dir, "data")

    def set_output_dir(self, output_dir: str | None):
        self._provided_output_dir = output_dir
        self._output_dir = output_dir if output_dir else os.path.abspath("results")

    def ensure_data_dir(self) -> str:
        os.makedirs(self._data_dir, exist_ok=True)
        return self._data_dir

    def ensure_output_dir(self) -> str:
        os.makedirs(self._output_dir, exist_ok=True)
        return self._output_dir

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of this Config."""
        return {
            "work_dir": self._provided_work_dir or "",
            "output_dir": self._provided_output_dir or "",
            "emulator_command": self._emulator_command or "",
            "iso_path": self.iso_path or "",
            "ftp_ip": self.ftp_ip or "",
            "ftp_ip_override": self.ftp_ip_override or "",
            "ftp_preferred_interface": self.ftp_preferred_interface or "",
            "test_failure_retries": self.test_failure_retries,
            # "timeout_seconds": self.timeout_seconds,  # Intentionally not saved.
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> Config:
        return Config(**config_dict)

    @classmethod
    def load(cls, config_file_path: str) -> Config | None:
        """Builds a Config instance from the given TOML file."""
        if not os.path.isfile(config_file_path):
            return None

        with open(config_file_path, "rb") as config_file:
            data = tomllib.load(config_file)

        return cls.from_dict(data)

    @classmethod
    def loads(cls, config_data: str) -> Config | None:
        """Builds a Config instance from the given TOML string."""
        return cls.from_dict(tomllib.loads(config_data))

    def store(self, config_file_path: str):
        """Saves this config to a file."""
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        with open(config_file_path, "wb") as config_file:
            tomli_w.dump(self.to_dict(), config_file)

    def stores(self) -> str:
        """Serializes this config to a string."""
        return tomli_w.dumps(self.to_dict())
