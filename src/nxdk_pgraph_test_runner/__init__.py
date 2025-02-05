# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: T201 `print` found

from __future__ import annotations

import argparse
import logging
import os
import sys

from platformdirs import user_config_dir

from nxdk_pgraph_test_runner.config import Config
from nxdk_pgraph_test_runner.runner import entrypoint

logger = logging.getLogger(__name__)


def run():
    """Parses program arguments and executes the runner."""
    default_config_path = os.path.join(user_config_dir("nxdk-pgraph-test-runner"), "config.toml")

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to the runner config file.", default=default_config_path)
    parser.add_argument(
        "--emulator-commandline",
        help=(
            "String used to launch the Xbox emulator. A `{ISO}` parameter will be replaced with the path to the "
            "tester xiso."
        ),
    )
    parser.add_argument("--iso-path", help="Path to the nxdk_pgraph_tests.iso xiso file.")
    parser.add_argument("--no-save-config", "-N", action="store_true", help="Do not update the config file.")
    parser.add_argument(
        "--override-ftp-ip",
        help="Use the given IP instead of the local IP when configuring the pgraph runner for artifact reporting.",
    )
    parser.add_argument(
        "--ftp-ip",
        help="Bind the FTP server to the given local IP.",
    )
    parser.add_argument(
        "--ftp-interface",
        "-I",
        help="Bind the FTP server to the given network interface (e.g., lo0).",
    )
    parser.add_argument(
        "--xbox-artifact-path",
        "-P",
        default="e:/nxdk_pgraph_tests",
        help="Xbox path into which test artifacts will be written",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        help="Enables verbose logging information",
        action="store_true",
    )
    parser.add_argument(
        "--timeout-seconds",
        "-T",
        help="Maximum period of time to execute the emulator before considering everything failed.",
        type=int,
    )
    parser.add_argument(
        "--work-dir",
        "-W",
        help="Host directory used to store temporary data",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Host directory used to store results of the runner",
    )
    parser.add_argument(
        "--test-failure-retries",
        "-r",
        default=1,
        help="Number of times to retry failed tests before considering them permanently failed",
        type=int,
    )
    parser.add_argument(
        "--max-consecutive-errors",
        default=5,
        help="Maximum number of emulator crashes without a clear cause before the run is aborted.",
        type=int,
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    config = Config.load(args.config)
    if not config:
        print("Using default config")
        config = Config()

    if args.emulator_commandline:
        config.set_emulator_command(args.emulator_commandline)
    if args.iso_path:
        config.iso_path = os.path.expanduser(args.iso_path)
    if args.ftp_ip:
        config.ftp_ip = args.ftp_ip
    if args.ftp_interface:
        config.ftp_preferred_interface = args.ftp_interface
    if args.override_ftp_ip:
        config.ftp_ip_override = args.override_ftp_ip
    if args.timeout_seconds:
        config.timeout_seconds = args.timeout_seconds
    if args.work_dir:
        config.set_work_dir = args.work_dir
    if args.output_dir:
        config.set_output_dir = args.output_dir
    config.test_failure_retries = args.test_failure_retries
    config.xbox_artifact_path = args.xbox_artifact_path
    config.max_consecutive_errors_before_termination = args.max_consecutive_errors

    if not args.no_save_config:
        logger.debug("Updating config file at %s", args.config)
        config.store(args.config)

    sys.exit(entrypoint(config))
