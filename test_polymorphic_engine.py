import unittest
from polymorphic_engine import PolymorphicEngine

class TestPolymorphicEngine(unittest.TestCase):

    def test_obfuscate(self):
        source_code = """
        int main() {
            int x = 1;
            if (x > 0) {
                return 1;
            } else {
                return 0;
            }
        }
        """
        engine = PolymorphicEngine(source_code)
        obfuscated_code = engine.obfuscate()
        self.assertIsInstance(obfuscated_code, str)
        self.assertNotEqual(source_code, obfuscated_code)
        self.assertIn("switch (state)", obfuscated_code)

if __name__ == '__main__':
    unittest.main()
