"""Owner configuration and fixed SSH command construction; no secret reads."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Config:
    host_alias: str = ""
    control_dir: str = ""
    vm_name: str = "ownmachine"
    guest_profile: str = "macos"
    connect_timeout_seconds: int = 15
    action_timeout_seconds: int = 30
    experimental_linux_background_input: bool = False

    def validate(self):
        if type(self.experimental_linux_background_input) is not bool or (self.experimental_linux_background_input and self.guest_profile != "omarchy"):
            raise ValueError("invalid_linux_background_opt_in")
        if self.guest_profile not in {"macos", "omarchy"}:
            raise ValueError("unsupported_guest_profile")
        for value in (self.host_alias, self.vm_name):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
                raise ValueError("invalid_configuration")
        for value in (self.connect_timeout_seconds, self.action_timeout_seconds):
            if type(value) is not int or not 1 <= value <= 120:
                raise ValueError("invalid_configuration")
        if not isinstance(self.control_dir, str) or (self.control_dir and not self.control_dir.startswith("/")):
            raise ValueError("invalid_control_directory")
        return self

    def ssh_argv(self, operation):
        self.validate()
        if operation not in {"status", "mcp", "start", "stop", "restart", "vnc"}:
            raise ValueError("unsupported_operation")
        # The relay also independently pins its one allowed VM. No arbitrary command.
        return ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "ForwardAgent=no", "-o", "ClearAllForwardings=yes",
                "-o", f"ConnectTimeout={self.connect_timeout_seconds}",
                "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
                self.host_alias, "ownmachine-host", operation, "--vm", self.vm_name]
