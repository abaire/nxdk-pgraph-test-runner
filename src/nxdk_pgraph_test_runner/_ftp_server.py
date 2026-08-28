from __future__ import annotations

import os
import time
from threading import Thread

import ifaddr
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class _RenamingFTPHandler(FTPHandler):
    """Renames incoming files to avoid restricted characters on Windows."""

    def handle_cmd(self, cmd, arg):
        notify = getattr(self.server, "notify_activity", None)
        if notify:
            notify()
        super().handle_cmd(cmd, arg)

    def on_file_received(self, file):
        notify = getattr(self.server, "notify_activity", None)
        if notify:
            notify()
        super().on_file_received(file)

    def on_incomplete_file_received(self, file):
        notify = getattr(self.server, "notify_activity", None)
        if notify:
            notify()
        super().on_incomplete_file_received(file)

    def ftp_STOR(self, file, mode="w"):  # noqa: N802 Function name `ftp_STOR` should be lowercase
        notify = getattr(self.server, "notify_activity", None)
        if notify:
            notify()
        sanitized_filename = file.replace("::", "~~")
        return super().ftp_STOR(sanitized_filename, mode)

    def ftp_APPE(self, file):  # noqa: N802 Function name `ftp_APPE` should be lowercase
        notify = getattr(self.server, "notify_activity", None)
        if notify:
            notify()
        return super().ftp_APPE(file)


class FtpServer(Thread):
    """Sets up an FTP server to receive files from the nxdk_pgraph_tests program."""

    _POLL_INTERVAL = 0.00001

    class NetworkInterfaceError(Exception):
        """Indicates that the network interface could not be automatically selected"""

    def __init__(
        self,
        data_dir: str,
        username: str | None = None,
        password: str | None = None,
        ftp_ip: str | None = None,
        ftp_interface: str | None = None,
    ) -> None:
        super().__init__(name="FtpServerThread", daemon=True)

        if not ftp_ip:
            ftp_ip = _select_ip_address(ftp_interface)

        self._data_dir = os.path.abspath(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

        self._username = username if username else "xbox"
        self._password = password if password else "xbox"
        self._last_activity_time: float = time.time()

        authorizer = DummyAuthorizer()
        authorizer.add_user(self._username, self._password, self._data_dir, perm="eamwMT")

        handler = _RenamingFTPHandler
        handler.authorizer = authorizer
        handler.timeout = 0

        self._server = FTPServer((ftp_ip, 0), handler)
        self._server.notify_activity = self.notify_activity  # type: ignore[attr-defined]
        self._server.max_cons = 8

        self._address, self._port = self._server.address
        self._server_running = False

    @property
    def last_activity_time(self) -> float:
        return self._last_activity_time

    def notify_activity(self) -> None:
        self._last_activity_time = time.time()

    def reset_activity_timer(self) -> None:
        self._last_activity_time = time.time()

    @property
    def address(self) -> str:
        return self._address

    @property
    def port(self) -> int:
        return self._port

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    def run(self):
        self._server_running = True
        try:
            self._server.serve_forever()
        except OSError:
            if self._server_running:
                raise

    def stop(self):
        """Stop the FTP server."""
        if not self._server_running:
            return
        self._server_running = False
        self._server.close()
        self._server.close_all()


def _get_ip_addresses() -> list[ifaddr.IP]:
    ret = []
    for adapter in ifaddr.get_adapters():
        adapter_ips: list[ifaddr.IP] = []
        for ip in adapter.ips:
            if not ip.is_IPv4:
                continue
            adapter_ips.append(ip)
        ret.extend(adapter_ips)
    return ret


def _select_ip_address(preferred_interface: str | None) -> str:
    ip_addresses = _get_ip_addresses()
    if not ip_addresses:
        msg = "No local network interfaces with addresses found"
        raise FtpServer.NetworkInterfaceError(msg)

    if len(ip_addresses) == 1:
        return str(ip_addresses[0].ip)

    if not preferred_interface:
        msg = f"Multiple local IP addresses found {ip_addresses}, one interface must be selected"
        raise FtpServer.NetworkInterfaceError(msg)

    for interface in ip_addresses:
        if interface.nice_name == preferred_interface:
            return str(interface.ip)

    msg = f"Multiple local IP addresses found {ip_addresses}, but none match preferred interface {preferred_interface}"
    raise FtpServer.NetworkInterfaceError(msg)
