# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: T201 `print` found

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, Any, NamedTuple

from nxdk_pgraph_test_runner._ftp_server import FtpServer
from nxdk_pgraph_test_runner._nxdk_pgraph_tester_config import NxdkPgraphTesterConfigManager
from nxdk_pgraph_test_runner._nxdk_pgraph_tester_progress_log import NxdkPgraphTesterProgressLog
from nxdk_pgraph_test_runner.emulator_output import EmulatorOutput

if TYPE_CHECKING:
    from nxdk_pgraph_test_runner._nxdk_pgraph_tester_test_output import NxdkPgraphTesterTestOutput
    from nxdk_pgraph_test_runner.config import Config
    from nxdk_pgraph_test_runner.host_profile import HostProfile

logger = logging.getLogger(__name__)

_RESULT_MANIFEST_FILENAME = "results.json"
_MODIFIED_PGRAPH_TESTER_ISO = "updated_pgraph_tester_iso.iso"
_TIMEOUT_STATUS = 10000


def validate_config(config: Config) -> list[str]:
    ret = []

    try:
        config.build_emulator_command("")
    except ValueError:
        ret.append("Missing command to launch the emulator")
    if not config.iso_path:
        ret.append("Missing path to iso")

    return ret


def _execute_emulator(emulator_command: list[str], config: Config) -> tuple[int, list[str], list[str]]:
    try:
        results = subprocess.run(
            emulator_command, capture_output=True, text=True, timeout=config.timeout_seconds, check=False
        )
    except FileNotFoundError:
        logger.exception("Failed to execute emulator")
        return 255, [], [f"Failed to execute command {emulator_command}"]

    return results.returncode, results.stdout.split("\n"), results.stderr.split("\n")


class RetryResults(NamedTuple):
    """Captures the results of retrying a previously failed test."""

    fully_qualified_name: str
    errors: list[str]
    success_result: NxdkPgraphTesterTestOutput | None = None

    def with_success_result(self, result: NxdkPgraphTesterTestOutput | None) -> RetryResults:
        return RetryResults(
            fully_qualified_name=self.fully_qualified_name, errors=self.errors.copy(), success_result=result
        )

    def to_obj(self) -> dict[str, Any]:
        if self.success_result:
            ret = self.success_result.to_obj()
        else:
            name, suite = self.fully_qualified_name.split("::")
            ret = {
                "suite": suite,
                "name": name,
            }

        ret["failures"] = self.errors.copy()
        ret["retries"] = len(self.errors)
        return ret


def _retry_failed_tests(
    config: Config,
    emulator_command: list[str],
    manager: NxdkPgraphTesterConfigManager,
    failed_tests: dict[str, str],
) -> dict[str, RetryResults]:
    ret: dict[str, RetryResults] = {}
    for fq_test_name, last_failure in failed_tests.items():
        retry_results = RetryResults(fully_qualified_name=fq_test_name, errors=[last_failure])

        if not manager.repack_with_only_tests({fq_test_name}):
            logger.error("Failed to repack with single test %s", fq_test_name)
            continue

        logger.info("Retrying previously failed test %s", fq_test_name)
        for _ in range(config.test_failure_retries):
            results = _execute_emulator_and_parse_progress_log(emulator_command, config)
            if not results:
                retry_results.errors.append("Timeout")
                break

            status, run_info, progress_log, _stderr = results
            if not status:
                retry_results = retry_results.with_success_result(progress_log.completed_tests.pop())
                break

            retry_results.errors.append(run_info.failure_info)

        ret[fq_test_name] = retry_results

    return ret


def _write_results(
    config: Config,
    output_path: str,
    passed_tests: list[NxdkPgraphTesterTestOutput],
    retry_results: dict[str, RetryResults],
) -> int:
    permanently_failed: list[RetryResults] = []
    flaky: list[RetryResults] = []

    for result in retry_results.values():
        if result.success_result:
            flaky.append(result)
        else:
            permanently_failed.append(result)

    result_manifest: dict[str, Any] = {
        "passed": {test_output.fully_qualified_name: test_output.to_obj() for test_output in passed_tests},
        "failed": {result.fully_qualified_name: result.to_obj() for result in permanently_failed},
        "flaky": {result.fully_qualified_name: result.to_obj() for result in flaky},
    }

    missing_artifacts: list[str] = []

    data_dir = config.ensure_data_dir()
    all_successes: list[NxdkPgraphTesterTestOutput] = [
        *passed_tests,
        *[retry.success_result for retry in flaky if retry.success_result],
    ]
    for test_output in all_successes:
        # Move the result artifacts for the test
        for artifact in test_output.artifacts:
            artifact_path = os.path.join(data_dir, artifact)
            if not os.path.isfile(artifact_path):
                missing_artifacts.append(artifact)
                continue

            artifact_destination = os.path.join(output_path, test_output.suite.replace(" ", "_"))
            os.makedirs(artifact_destination, exist_ok=True)

            shutil.move(artifact_path, os.path.join(artifact_destination, artifact.split("::")[1]))

    if missing_artifacts:
        result_manifest["missing_artifacts"] = missing_artifacts

    with open(os.path.join(output_path, _RESULT_MANIFEST_FILENAME), "w") as manifest_file:
        json.dump(result_manifest, manifest_file, ensure_ascii=True, indent=2, sort_keys=True)

    return 1


def get_output_dir_for_host_profile(host_profile: HostProfile, *, is_vulkan: bool = False) -> str:
    """Returns a directory hierarchy suitable for the information in the given HostProfile."""

    gl_info_prefix = "vk" if is_vulkan else "gl"

    components = [
        f"{host_profile.os_name}_{host_profile.cpu_model}",
        f"{gl_info_prefix}_{host_profile.gl_vendor}_{host_profile.gl_renderer}",
        f"gslv_{host_profile.gl_shading_language_version}",
    ]

    return os.path.join(*components).replace(" ", "_")


def get_output_directory(emulator_version_info: str, host_profile: HostProfile, *, is_vulkan: bool = False) -> str:
    """Returns a directory hierarchy suitable for the given emulator version and HostProfile."""
    output_dir = emulator_version_info if emulator_version_info else "__unknown_emulator__"
    return os.path.join(output_dir, get_output_dir_for_host_profile(host_profile, is_vulkan=is_vulkan))


def _prepare_output_path(config: Config, emulator_version_info: str, machine_info: str) -> str:
    output_dir = os.path.join(
        config.ensure_output_dir(),
        get_output_directory(emulator_version_info, config.host_profile, is_vulkan="\n- VK_" in machine_info),
    )

    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "machine_info.txt"), "w") as machine_info_file:
        machine_info_file.write(machine_info)

    return output_dir


def _execute_emulator_and_parse_results(
    emulator_command: list[str], config: Config
) -> tuple[int, EmulatorOutput, list[str]] | None:
    try:
        status, stdout, stderr = _execute_emulator(emulator_command, config)

    except subprocess.TimeoutExpired as err:
        logger.error("Timeout exceeded running %s.", emulator_command)  # noqa: TRY400 Use `logging.exception`
        status = _TIMEOUT_STATUS
        stdout = err.stdout.decode().split("\n") if err.stdout else []
        stderr = err.stderr.decode().split("\n") if err.stderr else []

    return status, EmulatorOutput.parse(stdout, stderr), stderr


def _execute_emulator_and_parse_progress_log(
    emulator_command: list[str], config: Config
) -> tuple[int, EmulatorOutput, NxdkPgraphTesterProgressLog, list[str]] | None:
    results = _execute_emulator_and_parse_results(emulator_command, config)
    if not results:
        return None

    status, run_info, stderr = results

    data_dir = config.ensure_data_dir()
    progress_log = NxdkPgraphTesterProgressLog(
        os.path.join(config.ensure_data_dir(), "nxdk_pgraph_tests_progress.log"), data_dir
    )

    return status, run_info, progress_log, stderr


def _run_tests(config: Config, iso_path: str) -> int:
    emulator_command = config.build_emulator_command(iso_path)

    manager = NxdkPgraphTesterConfigManager(config, iso_path)
    progress_log_path = os.path.join(config.ensure_data_dir(), "nxdk_pgraph_tests_progress.log")

    passed_tests: list[NxdkPgraphTesterTestOutput] = []
    failed_tests: dict[str, str] = {}

    last_exit_code = 0
    consecutive_unknown_failures = 0

    while True:
        results = _execute_emulator_and_parse_progress_log(emulator_command, config)
        if not results:
            return 255

        status, run_info, progress_log, stderr = results

        passed_tests.extend(progress_log.completed_tests)

        if not status:
            logger.info("Emulator indicates successful shutdown")
            break

        if progress_log.last_failed_test:
            failed_tests[progress_log.last_failed_test] = run_info.failure_info
            consecutive_unknown_failures = 0
        else:
            if last_exit_code != status:
                last_exit_code = status
                consecutive_unknown_failures = 0
            else:
                consecutive_unknown_failures += 1
                if consecutive_unknown_failures > config.max_consecutive_errors_before_termination:
                    logger.error(
                        "FATAL: Emulator exited with %d %d times where progress log does not indicate a specific test crash\n%s",
                        status,
                        consecutive_unknown_failures,
                        stderr,
                    )
                    return 1
            logger.error(
                "Emulator exited with code %d but progress log does not indicate a test crash. Retrying\n%s",
                status,
                stderr,
            )

        if not manager.repack_with_additional_tests_disabled(
            progress_log.completed_and_failed_fully_qualified_test_names
        ):
            logger.error("Failed to repack with new skipped tests")
            return 1

        if os.path.isfile(progress_log_path):
            os.unlink(progress_log_path)

    output_path = _prepare_output_path(config, run_info.emulator_version, run_info.machine_info)

    retry_results = _retry_failed_tests(config, emulator_command, manager, failed_tests)

    return _write_results(config, output_path, passed_tests, retry_results)


def _prepare_iso(config: Config, ftp_server: FtpServer) -> str | None:
    """Prepares a copy of the config ISO configured for the given FTP server."""
    manager = NxdkPgraphTesterConfigManager(config)
    iso_path = os.path.join(config.ensure_data_dir(), _MODIFIED_PGRAPH_TESTER_ISO)
    if not manager.repack_iso_fresh(
        iso_path, ftp_server.address, ftp_server.port, ftp_server.username, ftp_server.password, config.network_config
    ):
        return None

    return iso_path


def entrypoint(config: Config) -> int:
    """Program entrypoint."""

    errors = validate_config(config)
    if errors:
        for msg in errors:
            logger.error(msg)
        return 1

    shutil.rmtree(config.ensure_data_dir(), ignore_errors=True)

    ftp_server = FtpServer(
        data_dir=config.ensure_data_dir(), ftp_ip=config.ftp_ip, ftp_interface=config.ftp_preferred_interface
    )

    iso_path = _prepare_iso(config, ftp_server)
    if not iso_path:
        logger.error("Failed to prepare ISO for testing")
        return 1

    try:
        ftp_server.start()

        start = time.time()
        exit_value = _run_tests(config, iso_path)
        elapsed = time.time() - start

        print(f"Completed test suite in {elapsed} seconds")

        return exit_value

    finally:
        ftp_server.stop()
        ftp_server.join(timeout=2.0)
