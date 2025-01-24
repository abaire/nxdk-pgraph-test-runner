# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
import os
import shutil
import tarfile
import tempfile
from typing import TYPE_CHECKING, Any

import docker
import mergedeep

if TYPE_CHECKING:
    from collections.abc import Collection

    from docker.models.containers import Container

    from nxdk_pgraph_test_runner._config import Config

logger = logging.getLogger(__name__)

_REPACKER_IMAGE = "ghcr.io/abaire/nxdk-pgraph-test-repacker:latest"


class NxdkPgraphTesterConfigManager:
    def __init__(self, runner_config: Config, iso_path: str | None = None) -> None:
        self._runner_config = runner_config
        self._mount_dir = self._runner_config.ensure_mount_dir()
        self._data_dir = self._runner_config.ensure_data_dir()

        self.iso_path = iso_path if iso_path else self._runner_config.iso_path
        self.iso_filename = os.path.basename(self.iso_path)
        if not self.iso_filename:
            msg = "ISO file not set"
            raise ValueError(msg)
        if not os.path.isfile(self.iso_path):
            msg = f"Invalid path to ISO file '{self.iso_path}"
            raise ValueError(msg)

    def repack_iso_fresh(
        self, output_path: str, ftp_ip: str, ftp_port: int, ftp_username: str, ftp_password: str
    ) -> bool:
        """Repacks the nxdk_pgraph_tests iso with FTP enabled."""
        tester_config = self.extract_pgraph_tester_config()
        if not tester_config:
            tester_config = {"settings": {}}

        if not self.iso_filename:
            logger.error("No ISO file set")
            return False

        if self._runner_config.ftp_ip_override:
            ftp_ip = self._runner_config.ftp_ip_override

        mergedeep.merge(
            tester_config,
            {
                "settings": {
                    "disable_autorun": False,
                    "enable_autorun_immediately": True,
                    "enable_shutdown_on_completion": True,
                    "output_directory_path": self._runner_config.xbox_artifact_path,
                    "skip_tests_by_default": False,
                    "network": {
                        "enable": True,
                        "ftp": {
                            "ftp_ip": ftp_ip,
                            "ftp_port": ftp_port,
                            "ftp_user": ftp_username,
                            "ftp_password": ftp_password,
                        },
                    },
                }
            },
        )

        tester_config.pop("test_suites", None)

        # TODO: Verify that network: config_automatic/config_dhcp or static fields exist.

        return self._repack_config(tester_config, output_path)

    def extract_pgraph_tester_config(self) -> dict[str, Any] | None:
        """Extracts an existing JSON config from the nxdk_pgraph_tests ISO."""
        preferred_config = os.path.join(self._mount_dir, "nxdk_pgraph_tests_config.json")
        secondary_config = os.path.join(self._mount_dir, "sample-config.json")
        if os.path.isfile(preferred_config):
            os.unlink(preferred_config)
        if os.path.isfile(secondary_config):
            os.unlink(secondary_config)

        logger.info("Extracting configs from %s", self.iso_filename)
        iso_working_path = os.path.join(self._mount_dir, self.iso_filename)
        if iso_working_path != self.iso_path:
            shutil.copy(self.iso_path, iso_working_path)

        logger.info("Pulling repacker image and extracting config from %s...", self.iso_filename)
        client = docker.from_env()
        container = client.containers.run(
            _REPACKER_IMAGE,
            f"--iso {self.iso_filename} --extract-config",
            platform="linux/amd64",
            volumes=[f"{self._mount_dir}:/work"],
            detach=True,
        )

        exit_code = container.wait()["StatusCode"]
        if exit_code:
            logger.error("Failed to extract JSON config:\n%s", container.logs().decode("utf-8"))
            return None

        if os.path.isfile(preferred_config):
            logger.debug("Found preferred config!")
            ret = _parse_config_file(preferred_config)
            if ret:
                return ret

        if os.path.isfile(secondary_config):
            logger.debug("Found secondary config!")
            return _parse_config_file(secondary_config)

        return None

    def repack_with_additional_tests_disabled(self, names_to_disable: Collection[str]) -> bool:
        """Repacks the ISO with the given fully qualified test names disabled."""
        tester_config = self.extract_pgraph_tester_config()
        if not tester_config:
            msg = "Failed to extract existing nxdk_pgraph_tests config."
            raise ValueError(msg)

        skip_config = create_skip_config(names_to_disable)
        mergedeep.merge(tester_config, skip_config)

        return self._repack_config(tester_config, output_path=self.iso_path)

    def repack_with_only_tests(self, names_to_enable: Collection[str]) -> bool:
        """Repacks the ISO with the given fully qualified test name."""
        tester_config = self.extract_pgraph_tester_config()
        if not tester_config:
            msg = "Failed to extract existing nxdk_pgraph_tests config."
            raise ValueError(msg)

        if "settings" in tester_config:
            tester_config["settings"]["skip_tests_by_default"] = True

        test_suites: dict[str, Any] = {}
        for fq_name in names_to_enable:
            suite, name = fq_name.split("::")

            if suite not in test_suites:
                test_suites[suite] = {}

            test_suites[suite][name] = {"skipped": False}

        tester_config["test_suites"] = test_suites

        return self._repack_config(tester_config, output_path=self.iso_path)

    def _repack_config(self, tester_config: dict[str, Any], output_path: str) -> bool:
        """Repacks the source ISO with the given nxdk_pgraph_tests config data."""
        config_path = os.path.join(self._mount_dir, "updated-config.json")
        with open(config_path, "w", encoding="utf-8") as outfile:
            json.dump(tester_config, outfile, ensure_ascii=True, indent=2, sort_keys=True)

        config_path = os.path.relpath(config_path, self._mount_dir)

        expected_iso = os.path.join(self._mount_dir, "nxdk_pgraph_tests_xiso-updated.iso")
        if os.path.isfile(expected_iso):
            os.unlink(expected_iso)

        logger.info("Pulling repacker image and repacking %s with config %s...", self.iso_filename, config_path)
        client = docker.from_env()
        container = client.containers.run(
            _REPACKER_IMAGE,
            f"--iso {self.iso_filename} --config {config_path}",
            platform="linux/amd64",
            volumes=[f"{self._mount_dir}:/work"],
            detach=True,
        )

        exit_code = container.wait()["StatusCode"]
        if exit_code:
            logger.error("Failed to repack ISO with exit code %d:\n%s", exit_code, container.logs().decode("utf-8"))
            return False

        return self._extract_iso(container, output_path)

    def _extract_iso(self, container: Container, output_path: str) -> bool:
        repacker_output_file = "nxdk_pgraph_tests_xiso-updated.iso"

        expected_iso = os.path.join(self._mount_dir, repacker_output_file)
        if os.path.isfile(expected_iso):
            os.rename(expected_iso, output_path)
            return True

        logger.warning("Failed to find expected output file from repacker at %s", expected_iso)
        logger.warning(container.logs().decode("utf-8"))

        try:
            archive, stat = container.get_archive(f"/work/{repacker_output_file}")
        except docker.errors.NotFound:
            logger.exception("Failed to retrieve repacked ISO")
            return False

        with tempfile.NamedTemporaryFile() as tmpfile:
            for chunk in archive:
                tmpfile.write(chunk)
            tmpfile.flush()

            with tarfile.open(tmpfile.name) as tar:
                member = tar.getmember(repacker_output_file)
                tar.extractall(self._data_dir, members=[member], filter="data")

        expected_iso = os.path.join(self._data_dir, repacker_output_file)
        if not os.path.isfile(expected_iso):
            logger.error("Repack did not create expected ISO file:\n%s", container.logs().decode("utf-8"))
            return False

        os.rename(expected_iso, output_path)

        return True


def create_skip_config(names_to_disable: Collection[str]) -> dict[str, Any]:
    """Creates a 'test_suites' object with the given tests skipped."""

    ret: dict[str, Any] = {}
    skip_config = {"skipped": True}

    for fq_name in names_to_disable:
        suite, name = fq_name.split("::")

        if suite not in ret:
            ret[suite] = {}
        ret[suite][name] = skip_config

    return {"test_suites": ret}


def _parse_config_file(file_path: str) -> dict[str, Any] | None:
    with open(file_path, "rb") as infile:
        return json.load(infile)
