"""Retry utilities with exponential backoff.

This module provides a decorator for retrying operations that may
fail due to transient issues like network timeouts or temporary
service unavailability.
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from grovectl.utils.logging import get_logger

logger = get_logger("retry")

P = ParamSpec("P")
T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retrying functions with exponential backoff.

    Implements exponential backoff with optional jitter to prevent
    thundering herd problems when multiple clients retry simultaneously.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay in seconds (caps exponential growth).
        exponential_base: Base for exponential calculation (default 2).
        jitter: Add random jitter to delays to prevent thundering herd.
        exceptions: Tuple of exception types to catch and retry.
        on_retry: Optional callback called on each retry with (exception, attempt).

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry_with_backoff(max_attempts=3, base_delay=1.0)
        ... def fetch_data():
        ...     return requests.get("https://api.example.com/data")

        >>> @retry_with_backoff(
        ...     max_attempts=5,
        ...     exceptions=(ConnectionError, TimeoutError),
        ...     on_retry=lambda e, a: print(f"Retry {a}: {e}")
        ... )
        ... def connect_to_server():
        ...     ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay,
                    )

                    # Add jitter (0-50% of delay)
                    if jitter:
                        delay = delay * (1 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for "
                        f"{func.__name__}: {e}. Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class RetryContext:
    """Context manager for manual retry control.

    Provides a way to implement retry logic without decorators,
    useful when you need more control over the retry process.

    Args:
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay between retries.
        max_delay: Maximum delay cap.
        jitter: Whether to add random jitter.

    Example:
        >>> with RetryContext(max_attempts=3) as retry:
        ...     while retry.should_continue():
        ...         try:
        ...             result = make_request()
        ...             break
        ...         except ConnectionError as e:
        ...             retry.record_failure(e)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.attempt = 0
        self.last_exception: Exception | None = None

    def __enter__(self) -> RetryContext:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def should_continue(self) -> bool:
        """Check if another attempt should be made.

        Returns:
            True if more attempts are available.
        """
        return self.attempt < self.max_attempts

    def record_failure(self, exception: Exception) -> None:
        """Record a failed attempt and sleep before next try.

        Args:
            exception: The exception that caused the failure.

        Raises:
            The exception if max attempts reached.
        """
        self.attempt += 1
        self.last_exception = exception

        if self.attempt >= self.max_attempts:
            raise exception

        delay = min(
            self.base_delay * (2 ** (self.attempt - 1)),
            self.max_delay,
        )

        if self.jitter:
            delay = delay * (1 + random.random() * 0.5)

        logger.debug(
            f"Attempt {self.attempt}/{self.max_attempts} failed: {exception}. "
            f"Waiting {delay:.2f}s..."
        )

        time.sleep(delay)

    @property
    def attempts_remaining(self) -> int:
        """Number of attempts remaining."""
        return self.max_attempts - self.attempt
