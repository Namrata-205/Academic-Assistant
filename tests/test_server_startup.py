"""Hosting configuration exposes the service while preserving local defaults."""
import os
import unittest
from unittest.mock import patch
from server import startup_options


class ServerStartupTests(unittest.TestCase):
    def test_local_defaults_remain_loopback(self):
        with patch.dict(os.environ, {}, clear=True):
            args = startup_options([])
        self.assertEqual((args.host, args.port), ('127.0.0.1', 8000))

    def test_render_binds_all_interfaces_on_platform_port(self):
        with patch.dict(os.environ, {'RENDER': 'true', 'PORT': '10000'}, clear=True):
            args = startup_options([])
        self.assertEqual((args.host, args.port), ('0.0.0.0', 10000))

    def test_port_alone_enables_hosted_binding(self):
        with patch.dict(os.environ, {'PORT': '12345'}, clear=True):
            args = startup_options([])
        self.assertEqual((args.host, args.port), ('0.0.0.0', 12345))

    def test_explicit_flags_override_environment(self):
        with patch.dict(os.environ, {'HOST': '0.0.0.0', 'PORT': '10000'}, clear=True):
            args = startup_options(['--host', '127.0.0.1', '--port', '8765'])
        self.assertEqual((args.host, args.port), ('127.0.0.1', 8765))


if __name__ == '__main__':
    unittest.main()
