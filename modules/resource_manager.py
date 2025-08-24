#!/usr/bin/env python3
"""
Resource manager module for NFT Generator
Provides context managers for safe resource handling and cleanup.
"""

import logging
import threading
import time
from contextlib import contextmanager
from typing import Generator, Any, Optional, Callable, Dict
from pathlib import Path
from functools import wraps
from enum import Enum


class CircuitBreakerState(Enum):
    """States for the circuit breaker pattern."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation for handling repeated failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_recovery_time: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_recovery_time = expected_recovery_time

        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = None

        self._lock = threading.Lock()

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.state != CircuitBreakerState.OPEN:
            return False
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def can_execute(self) -> bool:
        """Check if operations can be executed."""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return True
            else:  # OPEN
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    logging.info("Circuit breaker entering HALF_OPEN state")
                    return True
                return False

    def record_success(self):
        """Record a successful operation."""
        with self._lock:
            self.success_count += 1

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.success_count >= 2:  # Require a few successes to fully recover
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logging.info("Circuit breaker CLOSED - service recovered")
                else:
                    logging.debug(f"Circuit breaker success count: {self.success_count}")

    def record_failure(self):
        """Record a failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.failure_count = self.failure_threshold  # Fast fail
                logging.warning("Circuit breaker re-opened during recovery attempt")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logging.error(f"Circuit breaker OPENED - too many failures ({self.failure_count})")

    def get_state_info(self) -> Dict[str, Any]:
        """Get current circuit breaker state information."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


class ResourceManager:
    """Centralized resource management with automatic cleanup and retry logic."""

    def __init__(self):
        self._resources = {}
        self._lock = threading.Lock()
        self.file_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,  # 30 seconds
            expected_recovery_time=300.0  # 5 minutes
        )

    def retry_on_failure(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (IOError, OSError, PermissionError)
    ):
        """
        Decorator for retrying operations on failure with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to multiply delay by after each retry
            exceptions: Tuple of exceptions to catch and retry on

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            # Last attempt failed, raise the exception
                            logging.error(f"Operation {func.__name__} failed after {max_retries + 1} attempts: {e}")
                            raise

                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        logging.warning(f"Attempt {attempt + 1} of {func.__name__} failed: {e}. "
                                       f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)

                # This should never be reached, but just in case
                if last_exception:
                    raise last_exception

            return wrapper
        return decorator

    @contextmanager
    def safe_file_operation(self, file_path: Path, mode: str = 'r', encoding: str = 'utf-8') -> Generator[Any, None, None]:
        """
        Context manager for safe file operations with automatic cleanup and circuit breaker.

        Args:
            file_path: Path to the file
            mode: File mode ('r', 'w', 'a', etc.)
            encoding: Text encoding for text modes

        Yields:
            File object
        """
        # Check circuit breaker
        if not self.file_circuit_breaker.can_execute():
            raise RuntimeError(f"Circuit breaker is OPEN for file operations. "
                             f"State: {self.file_circuit_breaker.get_state_info()}")

        file = None
        try:
            # Use binary mode for images, text mode for others
            if 'b' in mode:
                file = open(file_path, mode)
            else:
                file = open(file_path, mode, encoding=encoding)

            yield file

            # Record success
            self.file_circuit_breaker.record_success()

        except Exception as e:
            # Record failure
            self.file_circuit_breaker.record_failure()
            logging.error(f"Error in file operation {file_path} with mode {mode}: {str(e)}")
            raise
        finally:
            if file and not file.closed:
                try:
                    file.close()
                except Exception as e:
                    logging.warning(f"Failed to close file {file_path}: {e}")

    @contextmanager
    def safe_image_operation(self, image_path: Path) -> Generator[Any, None, None]:
        """
        Context manager for safe PIL Image operations with automatic cleanup.

        Args:
            image_path: Path to the image file

        Yields:
            PIL Image object
        """
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                yield img
        except Exception as e:
            logging.error(f"Error in image operation {image_path}: {str(e)}")
            raise

    @contextmanager
    def atomic_file_write(self, file_path: Path, encoding: str = 'utf-8') -> Generator[Any, None, None]:
        """
        Context manager for atomic file writes using temporary files.

        Args:
            file_path: Path to the target file
            encoding: Text encoding

        Yields:
            File object for writing
        """
        temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")

        try:
            with open(temp_path, 'w', encoding=encoding) as f:
                yield f

            # Atomic move after successful write
            import os
            os.replace(temp_path, file_path)
            logging.debug(f"Successfully wrote file atomically: {file_path}")

        except Exception as e:
            # Clean up temporary file on error
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            logging.error(f"Error in atomic file write {file_path}: {str(e)}")
            raise


# Global resource manager instance
resource_manager = ResourceManager()


# Convenience functions for easy access
def safe_file_operation(file_path: Path, mode: str = 'r', encoding: str = 'utf-8'):
    """Convenience function for safe file operations."""
    return resource_manager.safe_file_operation(file_path, mode, encoding)


def safe_image_operation(image_path: Path):
    """Convenience function for safe image operations."""
    return resource_manager.safe_image_operation(image_path)


def atomic_file_write(file_path: Path, encoding: str = 'utf-8'):
    """Convenience function for atomic file writes."""
    return resource_manager.atomic_file_write(file_path, encoding)


def retry_on_io_error(max_retries: int = 3, base_delay: float = 1.0):
    """Convenience decorator for retrying I/O operations."""
    return resource_manager.retry_on_failure(
        max_retries=max_retries,
        base_delay=base_delay,
        exceptions=(IOError, OSError, PermissionError)
    )


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get current circuit breaker status."""
    return resource_manager.file_circuit_breaker.get_state_info()