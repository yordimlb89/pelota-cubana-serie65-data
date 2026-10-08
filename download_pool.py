"""Two independent downloads at a time; results applied in original order."""
from concurrent.futures import ThreadPoolExecutor

ATTEMPT_TIMEOUTS = (20, 35)

def download_batch(function, items):
    def capture(item):
        try:
            return item, function(item), None
        except Exception as error:
            return item, None, error
    with ThreadPoolExecutor(max_workers=2) as executor:
        yield from executor.map(capture, items)
