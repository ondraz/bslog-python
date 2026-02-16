"""Tests for client error messages."""

import os
from unittest.mock import patch


class TestClientErrorMessages:
    def test_format_malformed_token_error_message(self) -> None:
        with patch.dict(os.environ, {"BETTERSTACK_API_TOKEN": "test-token"}, clear=True):
            os.environ.pop("BETTERSTACK_QUERY_USERNAME", None)
            os.environ.pop("BETTERSTACK_QUERY_PASSWORD", None)

            expected_error = (
                "Query API authentication failed: Malformed token\n\n"
                "This usually means your Query API credentials are not set.\n\n"
                "Current environment:\n"
                "  BETTERSTACK_API_TOKEN: ✓ Set\n"
                "  BETTERSTACK_QUERY_USERNAME: ✗ Not set\n"
                "  BETTERSTACK_QUERY_PASSWORD: ✗ Not set\n\n"
                "To fix this:\n"
                '1. Add these to your ~/.zshrc or ~/.bashrc:\n'
                '   export BETTERSTACK_QUERY_USERNAME="your_username"\n'
                '   export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
                "2. Reload your shell:\n"
                "   source ~/.zshrc\n\n"
                "3. Or set them for this session:\n"
                '   export BETTERSTACK_QUERY_USERNAME="your_username"\n'
                '   export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
                "To get Query API credentials:\n"
                "1. Go to Better Stack > Logs > Dashboards\n"
                '2. Click "Connect remotely"\n'
                "3. Create credentials and save them"
            )

            assert "BETTERSTACK_API_TOKEN: ✓ Set" in expected_error
            assert "BETTERSTACK_QUERY_USERNAME: ✗ Not set" in expected_error
            assert "To fix this:" in expected_error
            assert "Go to Better Stack > Logs > Dashboards" in expected_error

    def test_format_authentication_failure_message(self) -> None:
        expected_error = (
            "Query API authentication failed.\n\n"
            "The Query API requires separate credentials from your API token.\n"
            "To create credentials:\n"
            "1. Go to Better Stack > Logs > Dashboards\n"
            '2. Click "Connect remotely"\n'
            "3. Create credentials and save them\n\n"
            "Then set them as environment variables:\n"
            'export BETTERSTACK_QUERY_USERNAME="your_username"\n'
            'export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
            "Or pass them directly:\n"
            'bslog tail --username "user" --password "pass"'
        )

        assert "The Query API requires separate credentials" in expected_error
        assert "Go to Better Stack > Logs > Dashboards" in expected_error
        assert 'Click "Connect remotely"' in expected_error
        assert "export BETTERSTACK_QUERY_USERNAME" in expected_error
