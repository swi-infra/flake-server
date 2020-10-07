"""Config module to read server configuration files.

json format
"""
import os
import json


DEFAULT_CONFIG = "$FLAKE_TOOLS/host/config/server.json"


class Config(dict):
    """Configuration file handler."""

    def __init__(self, config=DEFAULT_CONFIG):
        self.base_config = os.path.expandvars(config)
        super(Config, self).__init__(self.config)

    @property
    def config(self):
        """Read server default config.

        Returns dictionary of values.
        """
        return self.read(self.base_config)

    def __str__(self):
        return json.dumps(self.copy(), indent=2, separators=(",", ": "))

    def read(self, config):
        """Read json file.

        Returns dictionary of values.
        """
        if not config or not os.path.exists(config):
            return {}
        with open(config) as json_file:
            return json.load(json_file)

    def merge(self, config):
        """Merge dictionaries together."""
        if not isinstance(config, dict):
            config = self.read(config)
        self.update(config)


class ServerConfig(Config):
    """Server configuration handler."""

    def __init__(self, config=DEFAULT_CONFIG):
        super(ServerConfig, self).__init__(config)


class ConfigHandler(Config):
    """Specific configuration file handler."""

    def __init__(self, config, server_config=DEFAULT_CONFIG):
        self.server = ServerConfig(server_config)
        super(ConfigHandler, self).__init__(config)
