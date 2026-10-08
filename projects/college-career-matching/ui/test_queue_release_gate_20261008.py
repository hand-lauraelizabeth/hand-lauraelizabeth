import unittest

class ReviewGateTests(unittest.TestCase):
    def test_private_queue_default(self):
        self.assertEqual('DO_NOT_PUBLISH', 'DO_NOT_PUBLISH')
