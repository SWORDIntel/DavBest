import unittest
from c2_redirector import generate_domains, construct_host_header

class TestC2Redirector(unittest.TestCase):

    def test_generate_domains(self):
        cdn_hostnames, frontable_domains = generate_domains(seed=123)
        self.assertIsInstance(cdn_hostnames, list)
        self.assertIsInstance(frontable_domains, list)
        self.assertGreater(len(cdn_hostnames), 0)
        self.assertGreater(len(frontable_domains), 0)

    def test_construct_host_header(self):
        cdn_hostnames, frontable_domains = generate_domains(seed=123)
        host_header = construct_host_header(cdn_hostnames, frontable_domains)
        self.assertIsInstance(host_header, str)
        self.assertIn("Host:", host_header)
        self.assertIn("X-Forwarded-Host:", host_header)

if __name__ == '__main__':
    unittest.main()
