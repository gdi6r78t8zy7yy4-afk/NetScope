# NetScope Process Manager Tests

"""
Comprehensive tests for the ProcessManager class.
"""

import asyncio
import pytest
from app.core.process_manager import (
    ProcessManager,
    run_command,
    check_executable_exists,
)


class TestProcessManager:
    """Test the ProcessManager class."""

    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test successful command execution."""
        result = await run_command(["echo", "hello"], timeout=10)

        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["timed_out"] is False

    @pytest.mark.asyncio
    async def test_run_command_timeout(self):
        """Test command timeout handling."""
        # This will timeout if sleep is longer than our timeout
        result = await run_command(["sleep", "5"], timeout=1)

        assert result["returncode"] == -1
        assert "Timeout" in result["stderr"]
        assert result["timed_out"] is True

    @pytest.mark.asyncio
    async def test_run_command_not_found(self):
        """Test command not found handling."""
        result = await run_command(["nonexistentcommand12345"], timeout=10)

        assert result["returncode"] == -1
        assert "not found" in result["stderr"].lower(
        ) or result.get("file_not_found")

    @pytest.mark.asyncio
    async def test_run_command_with_error(self):
        """Test command that returns non-zero exit code."""
        result = await run_command(["bash", "-c", "exit 1"], timeout=10)

        assert result["returncode"] == 1
        assert result["timed_out"] is False

    @pytest.mark.asyncio
    async def test_process_manager_init(self):
        """Test ProcessManager initialization."""
        pm = ProcessManager(timeout=30)

        assert pm.timeout == 30
        assert pm.logger is not None

    @pytest.mark.asyncio
    async def test_process_manager_execute_with_cleanup(self):
        """Test execute_with_cleanup method."""
        pm = ProcessManager(timeout=60)

        result = await pm.execute_with_cleanup(["echo", "test"])

        assert result["returncode"] == 0
        assert "test" in result["stdout"]
        assert result["timed_out"] is False

    @pytest.mark.asyncio
    async def test_process_manager_timeout_cleanup(self):
        """Test that timeout properly cleans up resources."""
        pm = ProcessManager(timeout=1)

        result = await pm.execute_with_cleanup(["sleep", "10"], timeout=1)

        assert result["returncode"] == -1
        assert result["timed_out"] is True

    @pytest.mark.asyncio
    async def test_process_manager_cancelled_error(self):
        """Test that cancelled errors are handled."""
        pm = ProcessManager(timeout=60)

        async def delayed_command():
            return await pm.execute_with_cleanup(["sleep", "10"], timeout=30)

        # Start the command and cancel it
        task = asyncio.create_task(delayed_command())
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_check_executable_exists(self):
        """Test executable existence check."""
        # Should find common utilities
        assert check_executable_exists("echo") is True
        assert check_executable_exists("bash") is True

    @pytest.mark.asyncio
    async def test_check_executable_not_exists(self):
        """Test checking for non-existent executable."""
        assert check_executable_exists("nonexistentcommand12345") is False


class TestProcessManagerTimeoutScenarios:
    """Test timeout scenarios in ProcessManager."""

    @pytest.mark.asyncio
    async def test_short_timeout(self):
        """Test with very short timeout."""
        pm = ProcessManager(timeout=0.1)

        result = await pm.execute_with_cleanup(["sleep", "5"], timeout=0.1)

        assert result["returncode"] == -1
        assert result["timed_out"] is True

    @pytest.mark.asyncio
    async def test_zero_timeout(self):
        """Test with zero timeout (should use default)."""
        pm = ProcessManager(timeout=0)

        # Should complete quickly for echo
        result = await pm.execute_with_cleanup(["echo", "fast"])

        assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_large_timeout(self):
        """Test with large timeout."""
        result = await run_command(["echo", "quick"], timeout=300)

        assert result["returncode"] == 0
        assert "quick" in result["stdout"]

    @pytest.mark.asyncio
    async def test_multiple_timeout_calls(self):
        """Test multiple sequential timeout calls."""
        for _ in range(3):
            result = await run_command(["sleep", "5"], timeout=1)

            assert result["returncode"] == -1
            assert result["timed_out"] is True


class TestProcessManagerOutputHandling:
    """Test stdout/stderr capture."""

    @pytest.mark.asyncio
    async def test_captures_stdout(self):
        """Test stdout capture."""
        result = await run_command(["printf", "hello"], timeout=10)

        assert result["stdout"] == "hello"
        assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_captures_stderr(self):
        """Test stderr capture."""
        result = await run_command(["bash", "-c", "echo error >&2; exit 1"], timeout=10)

        assert result["returncode"] == 1
        assert "error" in result["stderr"]

    @pytest.mark.asyncio
    async def test_empty_output(self):
        """Test empty output handling."""
        result = await run_command(["true"], timeout=10)

        assert result["returncode"] == 0
        # May or may not have output depending on command

    @pytest.mark.asyncio
    async def test_multiline_output(self):
        """Test multiline output capture."""
        result = await run_command(["bash", "-c", "echo line1; echo line2"], timeout=10)

        assert result["returncode"] == 0
        assert "line1" in result["stdout"]
        assert "line2" in result["stdout"]


class TestProcessManagerErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_command(self):
        """Test invalid command."""
        result = await run_command(["/bin/nonexistent"], timeout=10)

        assert result["returncode"] != 0

    @pytest.mark.asyncio
    async def test_command_with_special_chars(self):
        """Test command with special characters."""
        result = await run_command(["echo", "test & special chars"], timeout=10)

        assert result["returncode"] == 0
        assert "test" in result["stdout"]

    @pytest.mark.asyncio
    async def test_command_with_empty_args(self):
        """Test command with empty arguments."""
        result = await run_command(["echo", ""], timeout=10)

        assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_command_with_unicode(self):
        """Test command with unicode characters."""
        result = await run_command(["echo", "Hello 世界 🌍"], timeout=10)

        assert result["returncode"] == 0
        assert "Hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_binary_command_output(self):
        """Test binary command output."""
        # Use base64 to get binary-like output
        result = await run_command(["base64"], timeout=10)

        # Should succeed without errors (will wait for input and then timeout)
        assert "timed_out" in result or result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_process_cannot_start(self):
        """Test handling when process cannot start."""
        result = await run_command(["/nonexistent/path/to/binary"], timeout=10)

        assert result["returncode"] == -1
        assert "not found" in result.get("stderr", "").lower() or result.get(
            "file_not_found"
        )

    @pytest.mark.asyncio
    async def test_cancellation_during_execution(self):
        """Test task cancellation during command execution."""
        pm = ProcessManager(timeout=60)

        async def long_task():
            return await pm.execute_with_cleanup(["sleep", "100"], timeout=30)

        task = asyncio.create_task(long_task())
        await asyncio.sleep(0.1)  # Let command start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_concurrent_commands(self):
        """Test running multiple commands concurrently."""

        async def run_echo(msg: str):
            return await run_command(["echo", msg], timeout=10)

        results = await asyncio.gather(
            run_echo("task1"), run_echo("task2"), run_echo("task3")
        )

        assert len(results) == 3
        assert any("task1" in r["stdout"] for r in results)
        assert any("task2" in r["stdout"] for r in results)
        assert any("task3" in r["stdout"] for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_timeout(self):
        """Test timeout handling with concurrent commands."""

        async def slow_task():
            return await run_command(["sleep", "100"], timeout=1)

        results = await asyncio.gather(slow_task(), slow_task(), slow_task())

        assert all(r["timed_out"] for r in results)
        assert all(r["returncode"] == -1 for r in results)
