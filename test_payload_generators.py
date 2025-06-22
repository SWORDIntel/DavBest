import unittest
import os
import shutil # For cleaning up test directories
import time

# Assuming payload_generator.py, svg_payload_generator.py, css_payload_generator.py
# are in the same directory or accessible via PYTHONPATH.
from payload_generator import PayloadGenerator
from svg_payload_generator import SVGPayloadGenerator
from css_payload_generator import CSSPayloadGenerator

class TestPayloadGeneratorBase(unittest.TestCase):
    test_output_dir = "./test_payload_output_base"

    def setUp(self):
        # Ensure the test output directory is clean before each test
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        # We don't create it here; the generator should do it.

    def tearDown(self):
        # Clean up the test output directory after each test
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    class MockImplGenerator(PayloadGenerator):
        """A concrete implementation for testing PayloadGenerator."""
        def generate(self, payload_type, params=None):
            if payload_type == "mock_type":
                content = f"Mock content for {payload_type} with params {params}"
                filename = f"mock_{payload_type}.txt"
                return self.save_payload(filename, content)
            raise ValueError(f"Unsupported mock payload_type: {payload_type}")

        def get_available_payloads(self):
            return ["mock_type"]

    def test_output_directory_creation_default(self):
        """Test if default output directory ('./payload_output') is created."""
        default_dir = './payload_output_default_test' # Use a specific name for this test
        if os.path.exists(default_dir): shutil.rmtree(default_dir)

        # Test by instantiating (config is None, so default dir name is used by base class)
        # but we pass a config to ensure it uses *our* default_dir for this test
        generator = self.MockImplGenerator(config={'output_dir': default_dir})
        self.assertTrue(os.path.exists(default_dir))
        self.assertTrue(os.path.isdir(default_dir))
        shutil.rmtree(default_dir) # Clean up

    def test_output_directory_creation_custom(self):
        """Test if custom output directory is created."""
        generator = self.MockImplGenerator(config={'output_dir': self.test_output_dir})
        self.assertTrue(os.path.exists(self.test_output_dir))
        self.assertTrue(os.path.isdir(self.test_output_dir))

    def test_save_payload(self):
        """Test saving a payload to a file."""
        generator = self.MockImplGenerator(config={'output_dir': self.test_output_dir})
        filename = "test_payload.txt"
        content = "This is test content."

        filepath = generator.save_payload(filename, content)

        self.assertEqual(filepath, os.path.join(self.test_output_dir, filename))
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)

    def test_save_payload_io_error(self):
        """Test save_payload with a non-writable directory (simulated)."""
        # Create a file with the same name as the intended directory to cause an error
        # This is a bit tricky to reliably simulate cross-platform without admin rights
        # A more direct way is to mock os.makedirs or open, but for now, let's try this.
        bad_output_dir_path = os.path.join(self.test_output_dir, "non_writable_dir_sim")

        # Ensure parent test_output_dir exists
        os.makedirs(self.test_output_dir, exist_ok=True)

        with open(bad_output_dir_path, 'w') as f:
            f.write("I am a file, not a directory.")

        # This test now correctly expects the OSError during __init__ due to _create_output_dir
        with self.assertRaisesRegex(OSError, "exists but is not a directory"):
            self.MockImplGenerator(config={'output_dir': bad_output_dir_path})


class TestSVGPayloadGenerator(unittest.TestCase):
    test_output_dir = "./test_payload_output_svg"

    def setUp(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        # Generator will create it

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_generate_basic_svg(self):
        """Test generating a basic SVG payload."""
        generator = SVGPayloadGenerator(config={'output_dir': self.test_output_dir})
        filepath = generator.generate('basic')

        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.startswith(self.test_output_dir))
        self.assertTrue(filepath.endswith('.svg'))

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("<svg xmlns=\"http://www.w3.org/2000/svg\"", content)
        self.assertIn("<circle", content)
        self.assertIn("Test</text>", content) # Check for the text element

    def test_get_available_svg_payloads(self):
        """Test retrieving available SVG payload types."""
        generator = SVGPayloadGenerator() # No config needed for this
        payloads = generator.get_available_payloads()
        self.assertIsInstance(payloads, list)
        self.assertIn('basic', payloads)
        self.assertIn('script_tag', payloads) # Check a stubbed advanced type

    def test_generate_unknown_svg_type(self):
        """Test generating an unknown SVG payload type."""
        generator = SVGPayloadGenerator(config={'output_dir': self.test_output_dir})
        with self.assertRaises(ValueError):
            generator.generate('non_existent_type')


class TestCSSPayloadGenerator(unittest.TestCase):
    test_output_dir = "./test_payload_output_css"

    def setUp(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_generate_basic_css(self):
        """Test generating a basic CSS payload."""
        generator = CSSPayloadGenerator(config={'output_dir': self.test_output_dir})
        filepath = generator.generate('basic')

        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.startswith(self.test_output_dir))
        self.assertTrue(filepath.endswith('.css'))

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("/* WebDAV Security Test CSS */", content)
        self.assertIn("body {", content)
        self.assertIn(".test-element {", content)

    def test_get_available_css_payloads(self):
        """Test retrieving available CSS payload types."""
        generator = CSSPayloadGenerator()
        payloads = generator.get_available_payloads()
        self.assertIsInstance(payloads, list)
        self.assertIn('basic', payloads)
        self.assertIn('background_exfil', payloads) # Check a stubbed advanced type

    def test_generate_unknown_css_type(self):
        """Test generating an unknown CSS payload type."""
        generator = CSSPayloadGenerator(config={'output_dir': self.test_output_dir})
        with self.assertRaises(ValueError):
            generator.generate('non_existent_type')

if __name__ == '__main__':
    unittest.main()
