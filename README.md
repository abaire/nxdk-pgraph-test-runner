# nxdk-pgraph-test-runner

[![PyPI - Version](https://img.shields.io/pypi/v/nxdk-pgraph-test-runner.svg)](https://pypi.org/project/nxdk-pgraph-test-runner)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nxdk-pgraph-test-runner.svg)](https://pypi.org/project/nxdk-pgraph-test-runner)

-----

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [License](#license)

## Purpose

This test harness utilizes
the [nxdk_pgraph_tests](https://github.com/abaire/nxdk_pgraph_tests) project to
exercise the NV2A 3D accelerator on the original Microsoft Xbox. The runner is
intended to be used with an emulator (e.g., [xemu](https://xemu.app)) and is
able to detect and recover from crashes.

## Installation

### Prerequisites

* Docker - required
* An xbox emulator (e.g., [xemu](https://xemu.app)) - required

### pip installation

```console
# Optionally create a virtual env
#   pip -m venv .venv
#   source .venv/bin/activate

pip install nxdk-pgraph-test-runner

nxdk-pgraph-test-runner --help
```

## Configuration

A default config may be generated by running the `nxdk-pgraph-test-runner`
command.

### Emulator command line

`"emulator_command = /path/to/emulator {ISO}"`

The command may utilize the following macros:

* `{ISO}` - Replaced with the path to the `nxdk_pgraph_tests.iso` xiso file.

### Example invocation

This is a sample invocation that will run xemu against a previously downloaded
nxdk_pgraph_tests iso. It will create a `results` directory with the results of
the tests.

```shell
nxdk-pgraph-test-runner \
    --override-ftp-ip 10.0.2.2 \
    --iso-path ~/nxdk_pgraph_tests_xiso.iso \
    --emulator-command "/path/to/xemu -dvd_path \"{ISO}\"" \
    -I lo0
```

This assumes that xemu is configured to use NAT networking, so the IP reported
to the pgraph tester is set to the qemu `10.0.2.2` host address and the loopback
interface (-I `lo0`) is used.

## License

`nxdk-pgraph-test-runner` is distributed under the terms of
the [MIT](https://spdx.org/licenses/MIT.html) license.
