# NetScope Process Manager

"""
Process management utilities for subprocess execution with proper cleanup.
"""

import asyncio
from typing import Dict, Optional, Any

import structlog

logger = structlog.get_logger(__name__)


class ProcessManager:
    """
    Manages subprocess execution with proper resource cleanup.
    
    Features:
    - Automatic process termination on timeout
    - Graceful cancellation handling with process.wait() after kill
    - Process cleanup to avoid orphaned processes
    - Structured error reporting
    """
    
    def __init__(self, timeout: int = 60):
        # Default to 60 seconds if timeout is 0 or negative
        self.timeout = max(timeout, 1) if timeout is not None else 60
        self.logger = logger.bind(manager="process")
    
    async def execute_with_cleanup(
        self,
        cmd: list,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute command with proper cleanup on timeout/cancellation.
        
        Args:
            cmd: Command and arguments as list
            timeout: Override default timeout (None or 0 uses class default)
            
        Returns:
            Dict with stdout, stderr, returncode, and error info
            
        Raises:
            asyncio.CancelledError: If task is cancelled
        """
        # Handle timeout value: 0 or None means use default
        if timeout is not None and timeout > 0:
            actual_timeout = timeout
        else:
            actual_timeout = self.timeout
        
        process: Optional[asyncio.subprocess.Process] = None
        stdout_data: bytes = b""
        stderr_data: bytes = b""
        
        try:
            # Start the process - FileNotFoundError can be raised here if executable not found
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            except FileNotFoundError as e:
                self.logger.error("Executable not found", cmd=cmd, error=str(e))
                return {
                    "stdout": "",
                    "stderr": f"Executable not found: {cmd[0] if cmd else 'unknown'}",
                    "returncode": -1,
                    "file_not_found": True
                }
            
            # Wait for completion with timeout
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=actual_timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning("Process timed out, terminating", cmd=cmd)
                
                # Kill the process
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                
                # Wait for cleanup - CRITICAL: must wait after kill
                try:
                    if process.returncode is None:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception:
                    pass
                
                return {
                    "stdout": "",
                    "stderr": "Timeout exceeded",
                    "returncode": -1,
                    "timed_out": True
                }
                
            except asyncio.CancelledError:
                self.logger.warning("Process cancelled, terminating", cmd=cmd)
                
                # Kill the process on cancellation
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                
                # Wait for cleanup after kill
                try:
                    if process.returncode is None:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception:
                    pass
                
                raise
                
            except Exception as e:
                self.logger.error("Process execution error", cmd=cmd, error=str(e))
                
                # Attempt cleanup on other errors
                if process.returncode is None:
                    try:
                        process.kill()
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except Exception:
                        pass
                
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": -1,
                    "error": str(e)
                }
            
        finally:
            # Final cleanup: ensure process is cleaned up
            if process and process.returncode is None:
                try:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except (ProcessLookupError, asyncio.TimeoutError):
                    pass  # Process already terminated or timeout on wait
                except Exception as e:
                    self.logger.warning("Process cleanup error", error=str(e))
        
        return {
            "stdout": stdout_data.decode(),
            "stderr": stderr_data.decode(),
            "returncode": process.returncode if process else -1,
            "timed_out": False
        }


async def run_command(cmd: list, timeout: int = 60) -> Dict[str, Any]:
    """
    Execute a command with proper process management.
    
    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds (0 or None uses default)
        
    Returns:
        Dict with stdout, stderr, returncode
    """
    if timeout is not None and timeout > 0:
        pm = ProcessManager(timeout=timeout)
    else:
        pm = ProcessManager()  # Use default timeout
    return await pm.execute_with_cleanup(cmd)


def check_executable_exists(exec_name: str) -> bool:
    """
    Check if an executable exists in PATH.
    
    Args:
        exec_name: Name of the executable
        
    Returns:
        True if executable exists, False otherwise
    """
    import shutil
    
    return shutil.which(exec_name) is not None
