# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: T201 `print` found

from __future__ import annotations

from nxdk_pgraph_test_runner.emulator_output import parse_emulator_info

_XEMU_STDERR = [
    "xemu_version: 0.8.10",
    "xemu_branch: master",
    "xemu_commit: 5896b9dc91d2b8b94b2b30570e1e329b161c1453",
    "xemu_date: Wed Jan 29 19:14:08 UTC 2025",
    "xemu_settings_get_base_path: base path: /base_path/xemu/",
    "xemu_settings_get_path: config path: /base_path/xemu/xemu.toml",
    "CPU: ",
    "OS_Version: Version 14.6.1 (Build 23G93)",
    "GL_VENDOR: Apple",
    "GL_RENDERER: Apple M3 Max",
    "GL_VERSION: 4.1 Metal - 88.1",
    "GL_SHADING_LANGUAGE_VERSION: 4.10",
]


def test_parse_xemu_no_error():
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_STDERR.copy())

    assert version == "xemu-0.8.10-master-5896b9dc91d2b8b94b2b30570e1e329b161c1453"
    assert machine_info == "\n".join(_XEMU_STDERR)
    assert not failure_info


def test_parse_xemu_with_error():
    errors = ["Some error", "another error"]
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_STDERR + errors)

    assert version == "xemu-0.8.10-master-5896b9dc91d2b8b94b2b30570e1e329b161c1453"
    assert machine_info == "\n".join(_XEMU_STDERR)
    assert failure_info == "\n".join(errors)


_XEMU_VULKAN_STDDERR = [
    "Setting $HOME to /xemu-v0.8.20-x86_64.AppImage.home",
    "xemu_version: 0.8.20",
    "xemu_branch: master",
    "xemu_commit: 3bdb9e7fd4d6c9f5adec0543f1679d2943a0d092",
    "xemu_date: Sun Feb 16 00:00:03 UTC 2025",
    "xemu_settings_get_base_path: base path: /xemu-v0.8.20-x86_64.AppImage.home/.local/share/xemu/xemu/",
    "xemu_settings_get_path: config path: /xemu-v0.8.20-x86_64.AppImage.home/.local/share/xemu/xemu/xemu.toml",
    "CPU: Intel(R) Core(TM) i7-6700K CPU @ 4.00GHz",
    "OS_Version: Ubuntu 24.04.2 LTS",
    "GL_VENDOR: NVIDIA Corporation",
    "GL_RENDERER: NVIDIA GeForce GTX 1070/PCIe/SSE2",
    "GL_VERSION: 4.0.0 NVIDIA 570.86.15",
    "GL_SHADING_LANGUAGE_VERSION: 4.00 NVIDIA via Cg compiler",
    "Enabled instance extensions:",
    "- VK_KHR_surface",
    "- VK_KHR_xlib_surface",
    "- VK_KHR_get_physical_device_properties2",
    "- VK_KHR_external_semaphore_capabilities",
    "- VK_KHR_external_memory_capabilities",
    "Available physical devices:",
    "- NVIDIA GeForce GTX 1070",
    "- llvmpipe (LLVM 19.1.1, 256 bits)",
    "Selected physical device: NVIDIA GeForce GTX 1070",
    "- Vendor: 10de, Device: 1b81",
    "- Driver Version: 570.344.960",
    "Enabled device extensions:",
    "- VK_KHR_external_semaphore",
    "- VK_KHR_external_memory",
    "- VK_KHR_external_memory_fd",
    "- VK_KHR_external_semaphore_fd",
    "- VK_EXT_custom_border_color",
    "- VK_EXT_provoking_vertex",
    "- VK_EXT_memory_budget",
]


def test_parse_xemu_vulkan():
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_VULKAN_STDDERR.copy())

    assert version == "xemu-0.8.20-master-3bdb9e7fd4d6c9f5adec0543f1679d2943a0d092"
    assert machine_info == "\n".join(_XEMU_VULKAN_STDDERR[1:])
    assert not failure_info


def test_parse_xemu_vulkan_with_error():
    errors = ["Some error", "another error"]
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_VULKAN_STDDERR + errors)
    assert version == "xemu-0.8.20-master-3bdb9e7fd4d6c9f5adec0543f1679d2943a0d092"
    assert machine_info == "\n".join(_XEMU_VULKAN_STDDERR[1:])
    assert failure_info == "\n".join(errors)
