import time
import random
from config import SLEEP_BETWEEN_CALLS, MAX_RETRIES, BACKOFF_BASE


def call_with_retry(fn, *args, **kwargs):
    """
    Call fn(*args, **kwargs) with rate limiting and exponential backoff.
    Sleeps SLEEP_BETWEEN_CALLS before every call.
    On first 429, waits FIRST_429_WAIT seconds so the per-minute window resets.
    Then backs off exponentially up to MAX_RETRIES.
    """
    import openai
    from config import FIRST_429_WAIT
    time.sleep(SLEEP_BETWEEN_CALLS)
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except openai.RateLimitError:
            if attempt == MAX_RETRIES - 1:
                raise
            # First retry: wait long enough for the rate limit window to reset
            wait = FIRST_429_WAIT if attempt == 0 else BACKOFF_BASE ** attempt + random.uniform(0, 1)
            time.sleep(wait)
        except openai.APIStatusError as e:
            if e.status_code == 429:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = FIRST_429_WAIT if attempt == 0 else BACKOFF_BASE ** attempt + random.uniform(0, 1)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Exhausted retries")
