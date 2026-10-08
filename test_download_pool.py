import threading
import unittest
from download_pool import download_batch

class DownloadPool(unittest.TestCase):
    def test_two_downloads_overlap_with_stable_result_order(self):
        barrier = threading.Barrier(2, timeout=2)
        lock = threading.Lock()
        active = 0
        maximum = 0
        def work(value):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            barrier.wait()
            with lock:
                active -= 1
            return value * 2
        results = list(download_batch(work, range(4)))
        self.assertEqual(maximum, 2)
        self.assertEqual([(item, result) for item, result, error in results], [(0,0),(1,2),(2,4),(3,6)])
        self.assertTrue(all(error is None for _,_,error in results))

    def test_timeout_does_not_discard_other_downloads(self):
        def work(value):
            if value == 1:
                raise TimeoutError('source did not respond')
            return value
        results = list(download_batch(work, [0,1,2]))
        self.assertEqual(results[0], (0,0,None))
        self.assertIsInstance(results[1][2], TimeoutError)
        self.assertEqual(results[2], (2,2,None))

if __name__ == '__main__':
    unittest.main()
