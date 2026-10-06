"""Phase B3 crash-proofing tests (A.1 §1.1, §8.4, §8.5, §10.3, §10.5, §16 B3, §17.7, §24.2).

Covers the hardened calculator (pure AST validation, limits, typed
``math_error`` / ``internal_error``), and the three user-facing boundaries
(``tools/executor.py``, the CLI chat loop, the desktop workers): unexpected
exceptions become a fixed safe message with no traceback, no exception repr
and no raw internal text. No real network is used.
"""

from __future__ import annotations

import ast
import logging
from unittest.mock import patch

import pytest

import tools.calculator as calc
from core.safe_errors import (
    GENERIC_MESSAGE,
    INTERNAL_ERROR,
    MODEL_UNAVAILABLE_MESSAGE,
    SafeError,
    TypedSafeError,
    log_safe_exception,
    safe_error_message,
    to_safe_error,
)
from tools.calculator import (
    CalculatorError,
    CalculatorInternalError,
    CalculatorMathError,
    calculate,
    is_calculator_request,
    validate_expression,
)

# Dummy secret-like / path-like text, assembled at runtime so no literal
# credential-looking string lives in the repository.
FAKE_SECRET = "sk-" + "b3" + "CRASHPROOF" + "0123456789abcdef"
FAKE_PATH = "/home/" + "zoe-user" + "/.config/zoe/secret_token.json"
LEAK_TEXT = f"boom {FAKE_SECRET} at {FAKE_PATH}"

LEAK_MARKERS = ("Traceback", 'File "', FAKE_SECRET, FAKE_PATH, "RuntimeError(", "boom ")


def _assert_no_leak(text: str) -> None:
    for marker in LEAK_MARKERS:
        assert marker not in text, f"leaked {marker!r} in {text!r}"


def _math_error_for(expression: str) -> CalculatorMathError:
    with pytest.raises(CalculatorMathError) as info:
        calculate(expression)
    return info.value


# ---------------------------------------------------------------------------
# Division / modulo by zero -> typed math_error, never a crash
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expression", "reason"),
    [
        ("5 / 0", "division_by_zero"),
        ("5/0", "division_by_zero"),
        ("1 / (2 - 2)", "division_by_zero"),
        ("1/(2-2)", "division_by_zero"),
        ("7 % 0", "modulo_by_zero"),
        ("7 % (3 - 3)", "modulo_by_zero"),
        ("5.5 / 0.0", "division_by_zero"),
        ("what is 5 / 0?", "division_by_zero"),
        ("calculate 1 / (2 - 2)", "division_by_zero"),
    ],
)
def test_division_and_modulo_by_zero_are_typed_math_errors(expression: str, reason: str) -> None:
    error = _math_error_for(expression)
    assert error.error_type == "math_error"
    assert error.reason == reason
    assert "zero" in error.safe_message
    assert str(error) == error.safe_message
    _assert_no_leak(error.safe_message)


def test_typed_errors_keep_calculator_error_compatibility() -> None:
    """Existing ``except CalculatorError`` / ``except ValueError`` callers keep working."""
    for cls in (CalculatorMathError, CalculatorInternalError):
        assert issubclass(cls, CalculatorError)
    assert issubclass(CalculatorError, ValueError)
    assert issubclass(CalculatorError, TypedSafeError)
    with pytest.raises(CalculatorError):
        calculate("5 / 0")
    with pytest.raises(ValueError):
        calculate("7 % 0")
    with pytest.raises(CalculatorError) as info:
        calculate("Hello")
    assert type(info.value) is CalculatorError
    assert info.value.error_type == "invalid_arguments"
    assert CalculatorError("x").safe_message == "x"


def test_valid_arithmetic_still_works() -> None:
    assert calculate("2+2") == "4"
    assert calculate("10 * (5 + 2)") == "70"
    assert calculate("7 % 3") == "1"
    assert calculate("-3 + +5") == "2"
    assert calculate("what is 9 / 3?") == "3"
    assert calculate("1 / 4") == "0.25"


def test_to_safe_error_maps_math_error() -> None:
    safe = to_safe_error(_math_error_for("5 / 0"))
    assert safe == SafeError("math_error", safe.message)
    assert "zero" in safe.message


# ---------------------------------------------------------------------------
# Limits: length, parentheses, AST depth / nodes, integers, result, inf/nan
# ---------------------------------------------------------------------------


def test_limit_constants_match_contract() -> None:
    assert calc.MAX_EXPRESSION_CHARS == 256
    assert calc.MAX_PAREN_DEPTH == 16
    assert calc.MAX_AST_DEPTH == 128
    assert calc.MAX_AST_NODES == 256
    assert calc.MAX_INT_BITS == 1024
    assert calc.MAX_RESULT_CHARS == 64


def test_oversized_expression_rejected() -> None:
    expression = "1+" * 128 + "1"  # 257 chars
    assert len(expression) > 256
    error = _math_error_for(expression)
    assert error.reason == "expression_too_long"
    # Exactly at the limit is fine when the other limits allow it.
    assert len("1" * 64) <= 256
    assert calculate("1" * 64) == "1" * 64


def test_excessive_parentheses_rejected() -> None:
    error = _math_error_for("(" * 17 + "1" + ")" * 17)
    assert error.reason == "too_many_parentheses"
    assert calculate("(" * 16 + "1" + ")" * 16) == "1"


def test_excessive_ast_depth_rejected() -> None:
    expression = "-" * 130 + "1"
    with pytest.raises(CalculatorMathError) as info:
        validate_expression(expression)
    assert info.value.reason == "ast_too_deep"
    assert _math_error_for(expression).reason == "ast_too_deep"


def test_excessive_ast_nodes_rejected() -> None:
    expression = "1+" * 100 + "1"  # AST depth ~103 (< 128) but ~302 nodes (> 256)
    with pytest.raises(CalculatorMathError) as info:
        validate_expression(expression)
    assert info.value.reason == "too_many_nodes"


def test_huge_integer_literal_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1024 bits cannot be reached in 256 characters of + - * / %, so widen the
    # length limit to prove the integer limit itself is enforced.
    monkeypatch.setattr(calc, "MAX_EXPRESSION_CHARS", 2000)
    with pytest.raises(CalculatorMathError) as info:
        validate_expression("9" * 400)
    assert info.value.reason == "integer_too_large"


def test_huge_intermediate_integer_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calc, "MAX_EXPRESSION_CHARS", 2000)
    expression = "9" * 200 + " * " + "9" * 200  # literals ~665 bits, product ~1329 bits
    error = _math_error_for(expression)
    assert error.reason == "integer_too_large"


def test_integer_bit_limit_direct() -> None:
    with pytest.raises(CalculatorMathError) as info:
        calc._check_number(1 << 1024)
    assert info.value.reason == "integer_too_large"
    assert calc._check_number((1 << 1024) - 1) == (1 << 1024) - 1


def test_oversized_result_rejected() -> None:
    error = _math_error_for("9" * 70 + " + 1")
    assert error.reason == "result_too_long"
    error = _math_error_for("9" * 40 + " * " + "9" * 40)
    assert error.reason == "result_too_long"


def test_infinite_literal_rejected() -> None:
    with pytest.raises(CalculatorMathError) as info:
        validate_expression("1e999")
    assert info.value.reason == "non_finite"


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf"), float("nan")])
def test_inf_and_nan_results_rejected(monkeypatch: pytest.MonkeyPatch, bad_value: float) -> None:
    monkeypatch.setitem(calc._ALLOWED_BINARY_OPS, ast.Add, lambda _a, _b: bad_value)
    error = _math_error_for("1 + 2")
    assert error.reason == "non_finite"
    assert "finite" in error.safe_message


def test_overflow_error_becomes_math_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _overflow(_a: float, _b: float) -> float:
        raise OverflowError(LEAK_TEXT)

    monkeypatch.setitem(calc._ALLOWED_BINARY_OPS, ast.Mult, _overflow)
    error = _math_error_for("3 * 4")
    assert error.reason == "overflow"
    _assert_no_leak(error.safe_message)


# ---------------------------------------------------------------------------
# ** stays unsupported; only whitelisted syntax
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("expression", ["2 ** 3", "2**10", "9**9**9", "what is 2 ** 8?"])
def test_exponent_rejected(expression: str) -> None:
    with pytest.raises(CalculatorError) as info:
        calculate(expression)
    assert not isinstance(info.value, CalculatorMathError)
    assert info.value.error_type == "invalid_arguments"
    assert info.value.reason == "exponent_unsupported"
    assert "**" in info.value.safe_message
    assert is_calculator_request(expression) is False


def test_validate_expression_whitelist_rejects_other_syntax() -> None:
    for expression in ("2 ** 3", "2 // 3", "abs(1)", "x + 1", "True + 1", "1 << 2", "1 if 1 else 2", "[1]"):
        with pytest.raises(CalculatorError) as info:
            validate_expression(expression)
        assert not isinstance(info.value, CalculatorMathError), expression


def test_calculator_never_uses_eval() -> None:
    source = open(calc.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"eval", "exec", "compile"}


# ---------------------------------------------------------------------------
# Detection is pure: it parses / validates but never computes (§8.5, §17.7)
# ---------------------------------------------------------------------------


def test_detector_never_evaluates(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("detector must not evaluate")

    monkeypatch.setattr(calc, "_evaluate_node", _forbidden)
    monkeypatch.setattr(calc, "_evaluate_expression", _forbidden)
    for query in ("5 / 0", "1/(2-2)", "7 % 0", "what is 5 / 0?", "2+2", "9" * 300):
        assert is_calculator_request(query) is True, query
    assert is_calculator_request("Hello") is False
    assert is_calculator_request("2 ** 3") is False


def test_detector_survives_internal_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken(_query: str):
        raise RuntimeError(LEAK_TEXT)

    monkeypatch.setattr(calc, "_extract_calculator_expression", _broken)
    assert is_calculator_request("5 / 0") is False


# ---------------------------------------------------------------------------
# Unexpected calculator failures -> typed safe internal_error
# ---------------------------------------------------------------------------


def test_unexpected_calculator_error_is_typed_and_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    def _explode(_a: float, _b: float) -> float:
        raise RuntimeError(LEAK_TEXT)

    monkeypatch.setitem(calc._ALLOWED_BINARY_OPS, ast.Add, _explode)
    with pytest.raises(CalculatorInternalError) as info:
        calculate("1 + 2")
    error = info.value
    assert isinstance(error, CalculatorError)
    assert error.error_type == "internal_error"
    assert error.reason == "unexpected"
    assert error.__cause__ is None and error.__suppress_context__ is True
    _assert_no_leak(error.safe_message)
    _assert_no_leak(str(error))
    _assert_no_leak(repr(error))
    assert to_safe_error(error).code == INTERNAL_ERROR


def test_unexpected_evaluator_type_error_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _bad_node(_node):
        raise TypeError(LEAK_TEXT)

    monkeypatch.setattr(calc, "_evaluate_node", _bad_node)
    with pytest.raises(CalculatorInternalError) as info:
        calculate("4 - 1")
    _assert_no_leak(info.value.safe_message)


# ---------------------------------------------------------------------------
# Shared safe-error helper
# ---------------------------------------------------------------------------


def test_safe_error_helper_hides_raw_messages(caplog: pytest.LogCaptureFixture) -> None:
    try:
        raise RuntimeError(LEAK_TEXT)
    except RuntimeError as exc:
        assert safe_error_message(exc) == GENERIC_MESSAGE
        logger = logging.getLogger("zoe.test.b3")
        with caplog.at_level(logging.DEBUG, logger="zoe.test.b3"):
            safe = log_safe_exception(logger, "Unit", exc)
    assert safe == SafeError(INTERNAL_ERROR, GENERIC_MESSAGE)
    assert "RuntimeError" in caplog.text  # type name only
    _assert_no_leak(caplog.text.replace("(RuntimeError)", ""))
    assert all(record.exc_info is None for record in caplog.records)


def test_safe_error_helper_model_load_error_is_fixed_message() -> None:
    from brain.generation import ModelLoadError

    assert safe_error_message(ModelLoadError(LEAK_TEXT)) == MODEL_UNAVAILABLE_MESSAGE


# ---------------------------------------------------------------------------
# Boundary 1: tools/executor.py and the calculator plugin
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query", ["5 / 0", "1 / (2 - 2)", "7 % 0"])
def test_executor_returns_safe_math_error(query: str) -> None:
    from tools.executor import execute_tool

    with patch("brain.generation.load_model") as load_model:
        handled, message = execute_tool(query)
    load_model.assert_not_called()
    assert handled is True
    assert "zero" in message
    _assert_no_leak(message)


def test_executor_legacy_calculator_branch_returns_safe_math_error() -> None:
    import tools.executor as executor

    with patch.object(executor, "route_query", return_value="chat"), patch.object(
        executor, "_try_plugin_execute", return_value=(False, "")
    ):
        handled, message = executor.execute_tool("5 / 0")
    assert handled is True
    assert "zero" in message


def test_executor_invalid_calculator_input_falls_through() -> None:
    import tools.executor as executor

    with patch.object(executor, "route_query", return_value="chat"), patch.object(
        executor, "_try_plugin_execute", return_value=(False, "")
    ), patch.object(executor, "is_calculator_request", return_value=True):
        assert executor.execute_tool("2 ** 3") == (False, "")


def test_calculator_plugin_returns_safe_math_error() -> None:
    from plugins.builtin.calculator_plugin import _execute, _match

    assert _match("5 / 0") is True
    handled, message = _execute("5 / 0")
    assert handled is True and "zero" in message
    assert _execute("Hello") == (False, "")
    assert _execute("2 ** 3") == (False, "")


def test_executor_catch_all_hides_unexpected_errors(caplog: pytest.LogCaptureFixture) -> None:
    import tools.executor as executor

    def _broken_router(_query: str) -> str:
        raise RuntimeError(LEAK_TEXT)

    with caplog.at_level(logging.DEBUG), patch.object(executor, "route_query", _broken_router):
        handled, message = executor.execute_tool("anything at all")
    assert handled is True
    assert message == GENERIC_MESSAGE
    _assert_no_leak(message)
    _assert_no_leak(caplog.text)


def test_executor_keeps_b1_filesystem_errors() -> None:
    """B1 typed filesystem errors keep their own safe messages (not the generic one)."""
    import tools.executor as executor
    from tools.fs_policy import FilesystemError

    refusal = FilesystemError("Access to that path is not allowed", "outside_workspace")
    with patch.object(executor, "route_query", return_value="filesystem"), patch.object(
        executor, "read_file", side_effect=refusal
    ):
        handled, message = executor.execute_tool("read file notes.txt")
    assert handled is True
    assert message == str(refusal)
    assert message != GENERIC_MESSAGE


# ---------------------------------------------------------------------------
# Boundary 2: CLI chat loop and entry point
# ---------------------------------------------------------------------------


class _StartupReport:
    diagnostic_lines = ["startup ok"]


def _run_cli_chat(monkeypatch: pytest.MonkeyPatch, inputs: list[str], generate) -> None:
    import cli.main as cli_main

    feed = iter(inputs)

    def _fake_input(_prompt: str = "") -> str:
        try:
            return next(feed)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", _fake_input)
    monkeypatch.setattr("brain.pipeline._prepare_chat_session", lambda: None)
    monkeypatch.setattr("deployment.startup.run_startup_sequence", lambda *a, **k: _StartupReport())
    monkeypatch.setattr("brain.model.generate_response", generate)
    cli_main._run_chat_loop()


def test_cli_chat_turn_exception_prints_safe_message_and_continues(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[str] = []

    def _generate(prompt: str) -> str:
        calls.append(prompt)
        if prompt == "explode":
            raise RuntimeError(LEAK_TEXT)
        return f"echo {prompt}"

    with caplog.at_level(logging.DEBUG):
        _run_cli_chat(monkeypatch, ["explode", "hello", "exit"], _generate)
    out = capsys.readouterr()
    assert calls == ["explode", "hello"]
    assert f"Zoe: {GENERIC_MESSAGE}" in out.out
    assert "Zoe: echo hello" in out.out
    _assert_no_leak(out.out + out.err)
    _assert_no_leak(caplog.text)


def test_cli_model_load_error_shows_fixed_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from brain.model import ModelLoadError

    def _generate(_prompt: str) -> str:
        raise ModelLoadError(LEAK_TEXT)

    _run_cli_chat(monkeypatch, ["hi", "never reached"], _generate)
    out = capsys.readouterr()
    assert f"Zoe: {MODEL_UNAVAILABLE_MESSAGE}" in out.out
    _assert_no_leak(out.out + out.err)


def test_cli_keyboard_interrupt_during_turn_is_cancelled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _generate(prompt: str) -> str:
        if prompt == "slow":
            raise KeyboardInterrupt
        return "fine"

    _run_cli_chat(monkeypatch, ["slow", "next", "quit"], _generate)
    out = capsys.readouterr()
    assert "Zoe: Cancelled." in out.out
    assert "Zoe: fine" in out.out
    _assert_no_leak(out.out + out.err)


def test_cli_startup_failure_is_safe(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import cli.main as cli_main

    def _broken_startup(*_a, **_k):
        raise OSError(LEAK_TEXT)

    monkeypatch.setattr("builtins.input", lambda _p="": "exit")
    monkeypatch.setattr("brain.pipeline._prepare_chat_session", lambda: None)
    monkeypatch.setattr("deployment.startup.run_startup_sequence", _broken_startup)
    cli_main._run_chat_loop()
    out = capsys.readouterr()
    assert f"Zoe: {GENERIC_MESSAGE}" in out.out
    _assert_no_leak(out.out + out.err)


def test_cli_divide_by_zero_through_real_pipeline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """§16 B3 acceptance: ``5 / 0`` returns a safe message in the CLI path."""
    import brain.pipeline as pipeline

    def _no_model(*_a, **_k):
        raise AssertionError("the model must not load for 5 / 0")

    monkeypatch.setattr("memory.intelligence.memory_review.respond_to_profile_query", lambda _p: None)
    monkeypatch.setattr(pipeline, "_try_save_memory", lambda _p: False)
    monkeypatch.setattr(pipeline, "_handle_explicit_web_turn", lambda _p, _n: None)
    monkeypatch.setattr(pipeline, "_complete_turn", lambda _p, reply: reply)
    monkeypatch.setattr(pipeline, "load_model", _no_model)
    monkeypatch.setattr("plugins.manager.initialize_plugins", lambda *a, **k: None)

    _run_cli_chat(monkeypatch, ["5 / 0", "1 / (2 - 2)", "7 % 0", "exit"], pipeline.generate_response)
    out = capsys.readouterr()
    assert out.out.count("Zoe: I can't calculate that:") == 3
    assert "division by zero" in out.out and "modulo by zero" in out.out
    _assert_no_leak(out.out + out.err)


def test_cli_main_entry_point_hides_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import cli.main as cli_main

    def _broken_app() -> None:
        raise RuntimeError(LEAK_TEXT)

    monkeypatch.setattr(cli_main, "app", _broken_app)
    with pytest.raises(SystemExit) as info:
        cli_main.main()
    assert info.value.code == 1
    out = capsys.readouterr()
    assert GENERIC_MESSAGE in out.out
    _assert_no_leak(out.out + out.err)


def test_cli_main_entry_point_preserves_exit_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    import cli.main as cli_main

    def _exit_two() -> None:
        raise SystemExit(2)

    monkeypatch.setattr(cli_main, "app", _exit_two)
    with pytest.raises(SystemExit) as info:
        cli_main.main()
    assert info.value.code == 2


# ---------------------------------------------------------------------------
# Boundary 3: desktop workers (offscreen Qt via the shared qapp fixture)
# ---------------------------------------------------------------------------


def test_desktop_chat_worker_emits_safe_error(qapp, caplog: pytest.LogCaptureFixture) -> None:
    from desktop.workers import ChatWorker

    worker = ChatWorker("explode")
    completed: list[str] = []
    failed: list[str] = []
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)

    with caplog.at_level(logging.DEBUG), patch(
        "brain.pipeline.generate_response", side_effect=RuntimeError(LEAK_TEXT)
    ):
        worker.run()  # synchronous: no thread needed to observe the signals
    assert completed == []
    assert failed == [GENERIC_MESSAGE]
    _assert_no_leak(failed[0])
    _assert_no_leak(caplog.text)


def test_desktop_chat_worker_divide_by_zero_is_safe_reply(qapp) -> None:
    from desktop.workers import ChatWorker
    from tools.executor import execute_tool

    def _tool_only(prompt: str) -> str:
        handled, reply = execute_tool(prompt)
        assert handled
        return reply

    worker = ChatWorker("5 / 0")
    completed: list[str] = []
    failed: list[str] = []
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)
    with patch("brain.pipeline.generate_response", _tool_only):
        worker.run()
    assert failed == []
    assert len(completed) == 1 and "division by zero" in completed[0]


def test_desktop_vision_worker_emits_safe_error(qapp) -> None:
    from brain.generation import ModelLoadError
    from desktop.workers import VisionWorker

    for error, expected in ((RuntimeError(LEAK_TEXT), GENERIC_MESSAGE), (ModelLoadError(LEAK_TEXT), MODEL_UNAVAILABLE_MESSAGE)):
        worker = VisionWorker(FAKE_PATH, "describe")
        failed: list[str] = []
        worker.failed.connect(failed.append)
        with patch("brain.pipeline.generate_image_response", side_effect=error):
            worker.run()
        assert failed == [expected]
        _assert_no_leak(failed[0])


def test_desktop_function_worker_emits_safe_error(qapp, caplog: pytest.LogCaptureFixture) -> None:
    from desktop.workers import FunctionWorker

    def _boom() -> None:
        raise ValueError(LEAK_TEXT)

    worker = FunctionWorker("index_notes", _boom)
    failed: list[str] = []
    finished: list[object] = []
    worker.signals.failed.connect(failed.append)
    worker.signals.finished.connect(finished.append)
    with caplog.at_level(logging.DEBUG):
        worker.run()
    assert finished == []
    assert failed == [GENERIC_MESSAGE]
    _assert_no_leak(failed[0])
    _assert_no_leak(caplog.text)
    assert all(record.exc_info is None for record in caplog.records)


def test_desktop_startup_worker_emits_safe_warning(qapp) -> None:
    from desktop.workers import StartupWorker

    worker = StartupWorker()
    lines: list[str] = []
    finished: list[list[str]] = []
    worker.line_ready.connect(lines.append)
    worker.finished_ok.connect(finished.append)
    with patch("deployment.config.load_config", side_effect=OSError(LEAK_TEXT)):
        worker.run()
    assert finished == [[f"Startup warning: {GENERIC_MESSAGE}"]]
    for line in lines + finished[0]:
        _assert_no_leak(line)


# ---------------------------------------------------------------------------
# Cross-boundary: no traceback leakage anywhere
# ---------------------------------------------------------------------------


def test_no_traceback_leakage_across_boundaries(
    qapp, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    import tools.executor as executor
    from desktop.workers import ChatWorker, FunctionWorker

    def _raise(*_a, **_k):
        raise RuntimeError(LEAK_TEXT)

    surfaced: list[str] = []
    with caplog.at_level(logging.DEBUG):
        # Executor
        with patch.object(executor, "route_query", _raise):
            surfaced.append(executor.execute_tool("anything")[1])
        # CLI
        _run_cli_chat(monkeypatch, ["boom", "exit"], _raise)
        # Desktop
        chat = ChatWorker("boom")
        chat.failed.connect(surfaced.append)
        with patch("brain.pipeline.generate_response", _raise):
            chat.run()
        fn_worker = FunctionWorker("job", _raise)
        fn_worker.signals.failed.connect(surfaced.append)
        fn_worker.run()

    out = capsys.readouterr()
    surfaced.append(out.out)
    surfaced.append(out.err)
    assert len(surfaced) == 5
    for text in surfaced:
        _assert_no_leak(text)
    _assert_no_leak(caplog.text)
    assert all(record.exc_info is None for record in caplog.records)
    assert GENERIC_MESSAGE in out.out
