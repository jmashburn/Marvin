"""Unit tests for the AI execution logging policy.

`_logging_policy` resolves (log_inputs, log_outputs) from the workspace's logging_config.
Defaults preserve prior behavior: outputs logged, inputs not.
"""

from unittest.mock import MagicMock

from marvin.routes.ai.operations_controller import AIOperationsController


def _policy(logging_config):
    fake = MagicMock()
    settings = MagicMock()
    settings.logging_config = logging_config
    fake.session.query.return_value.filter_by.return_value.first.return_value = settings
    return AIOperationsController._logging_policy(fake)


def test_default_when_unset_logs_outputs_not_inputs():
    assert _policy(None) == (False, True)


def test_empty_config_uses_defaults():
    assert _policy({}) == (False, True)


def test_opt_in_to_input_logging():
    assert _policy({"log_inputs": True}) == (True, True)


def test_opt_out_of_output_logging():
    assert _policy({"log_outputs": False}) == (False, False)


def test_no_settings_row_uses_defaults():
    fake = MagicMock()
    fake.session.query.return_value.filter_by.return_value.first.return_value = None
    assert AIOperationsController._logging_policy(fake) == (False, True)
