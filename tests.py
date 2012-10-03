import unittest

from srt import Timecode


class TimecodeTestCase(unittest.TestCase):    
    
    
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        
    def test_copy(self):
        first = Timecode(500)
        second = first.copy()
        self.assertEqual(first.milliseconds(), second.milliseconds())
        self.assertIsNot(first, second)
        
    def test_equals(self):
        first = Timecode(500)
        second = Timecode(500)
        self.assertEqual(first, second)
        
    def test_add(self):
        first = Timecode(300)
        second = Timecode(200)
        the_sum = first + second
        
        self.assertEqual(the_sum, Timecode(500))
        self.assertIsNot(the_sum, first)
        self.assertIsNot(the_sum, second)
        
    def test_sub(self):
        first = Timecode(400)
        second = Timecode(300)
        
        first_sub = first - second
        second_sub = second - first
        
        self.assertEqual(first_sub, Timecode(100))
        self.assertEqual(second_sub, Timecode(-100))
        
        self.assertIsNot(second_sub, first)
        self.assertIsNot(second_sub, second)
        self.assertIsNot(first_sub, first)
        self.assertIsNot(first_sub, second)
        
    def test_lt(self):
        first = Timecode(300)
        second = Timecode(200)
        
        self.assertFalse(first < second)
        self.assertTrue(second < first)

    def test_from_string(self):
        from_string_tests = [
            ('1', 1000),
            ('12:34:56,789', 45296789),
            ('-01:02:03,004', -3723004),
            ('1:2:3,4', 3723004),
            ('00:00:00,004', 4),
            (',4', 4),
            ('00:00:03,000', 3000),
            ('3', 3000),
            ('3,4', 3004),
            ('00:00:03,004', 3004),
            ('-1:2', -62000),
            ('00:01:02,000', 62000),
            ('1:2,3', 62003),
            ('00:01:02,003', 62003),
            ('1:2:3', 3723000),
            ('01:02:03,000', 3723000),
        ]

        for test, expected in from_string_tests:
            foo = Timecode.from_string(test)
            self.assertEqual(foo.milliseconds(), expected, '%s not %d!' % (test, expected))

    def test_to_string(self):
        to_string_tests = [
            (1, '00:00:00,001'),
            (-2001, '-00:00:02,001'),
            (63001, '00:01:03,001'),
            (7384005, '02:03:04,005')
        ]
        
        for test, expected in to_string_tests:
            foo = Timecode(test)
            self.assertEqual(str(foo), expected, 'str(Timecode(%d)) not %s!' % (test, expected))


class SRTFrameTestCase(unittest.TestCase):
    
    
    


if __name__ == "__main__":
    unittest.main()