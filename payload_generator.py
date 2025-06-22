import os
import logging
import shutil # Added for cleanup in example usage

# Configure basic logging for this module if needed, or rely on application-level config
# Using a basic configuration for the logger if no handlers are found.
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class PayloadGenerator:
    """Base class for all payload generators."""

    def __init__(self, config=None):
        """
        Initialize with optional configuration.

        Args:
            config (dict, optional): Configuration dictionary.
                                     Expected keys: 'output_dir'.
        """
        self.config = config or {}
        # Default output_dir to './payloads' relative to where script is run,
        # or an absolute path if provided in config.
        # Ensure output_dir is an absolute path for consistency
        self.output_dir = os.path.abspath(self.config.get('output_dir', os.path.join(os.getcwd(), 'payloads')))

        self._create_output_dir()

    def _create_output_dir(self):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                logger.info(f"Created output directory: {self.output_dir}")
            except OSError as e:
                logger.error(f"Failed to create output directory {self.output_dir}: {e}")
                # For now, log error and continue; save_payload will fail if dir doesn't exist.
                # Depending on strictness, could re-raise e here.
                pass

    def generate(self, payload_type, params=None):
        """
        Generate a payload of the specified type.
        This method must be implemented by subclasses.

        Args:
            payload_type (str): The specific type of payload to generate (e.g., 'basic', 'script_tag').
            params (dict, optional): Parameters for tailoring the payload (e.g., js_code, callback_url).

        Returns:
            str: The filepath of the generated payload.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
            ValueError: If the payload_type is unknown or unsupported by the subclass.
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def save_payload(self, filename, content):
        """
        Save payload content to a file in the configured output directory.

        Args:
            filename (str): The name of the file to save the payload to.
            content (str): The string content of the payload.

        Returns:
            str: The full, absolute path to the saved payload file.

        Raises:
            IOError: If there's an error writing the file or if output_dir cannot be created.
        """
        # Ensure the output directory exists before attempting to save
        if not os.path.isdir(self.output_dir): # Check if it's a directory
            logger.warning(f"Output path {self.output_dir} is not a directory or does not exist. Attempting to create.")
            self._create_output_dir()
            if not os.path.isdir(self.output_dir):
                 err_msg = f"Output directory {self.output_dir} does not exist and could not be created."
                 logger.error(err_msg)
                 raise IOError(err_msg)

        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Payload saved to: {filepath}")
            return os.path.abspath(filepath)
        except IOError as e:
            logger.error(f"Failed to save payload to {filepath}: {e}")
            raise

    def get_available_payloads(self):
        """
        Return a list of available payload types for this generator.
        This method must be implemented by subclasses.

        Returns:
            list[str]: A list of strings representing available payload types.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement get_available_payloads()")

if __name__ == '__main__':
    # This basicConfig will set up the root logger if no handlers are configured yet.
    # It's useful for seeing log messages from the example usage.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')

    logger.info("PayloadGenerator base class demonstration.")

    test_output_dir = os.path.abspath('./generated_payloads_test')
    test_config = {'output_dir': test_output_dir}

    logger.info(f"Test output directory will be: {test_output_dir}")

    # Clean up previous test directory if it exists
    if os.path.exists(test_output_dir):
        logger.info(f"Removing existing test directory: {test_output_dir}")
        try:
            shutil.rmtree(test_output_dir)
        except Exception as e:
            logger.error(f"Error removing old test directory {test_output_dir}: {e}")


    class DummyPayloadGenerator(PayloadGenerator):
        def generate(self, payload_type, params=None):
            if payload_type == "dummy_test":
                content = f"This is a dummy payload of type: {payload_type}\nParams: {params}"
                filename = f"{payload_type}.txt"
                # save_payload is called by the generate method in the actual implementation plan
                # For this dummy, we call it directly to test it.
                return self.save_payload(filename, content)
            raise ValueError(f"Unknown payload type: {payload_type}")

        def get_available_payloads(self):
            return ["dummy_test"]

    logger.info(f"Attempting to initialize DummyPayloadGenerator with output directory: {test_output_dir}")
    try:
        generator = DummyPayloadGenerator(config=test_config)
        logger.info(f"DummyPayloadGenerator initialized. Output directory is: {generator.output_dir}")

        if os.path.isdir(generator.output_dir):
            logger.info(f"Output directory '{generator.output_dir}' was created successfully (or verified).")
        else:
            logger.error(f"CRITICAL ERROR: Output directory '{generator.output_dir}' was NOT created/found.")

        logger.info("Testing payload generation and saving (via dummy generator):")
        try:
            saved_path = generator.generate("dummy_test", params={"data": "test_data_123"})
            logger.info(f"Dummy payload generated and saved to: {saved_path}")
            if os.path.exists(saved_path):
                logger.info("File content verification:")
                with open(saved_path, 'r', encoding='utf-8') as f_read:
                    file_content = f_read.read()
                    logger.info(f"Read content: <<<{file_content}>>>")
                    if "test_data_123" in file_content:
                        logger.info("Content verification successful.")
                    else:
                        logger.error("Content verification FAILED. 'test_data_123' not found.")
            else:
                logger.error(f"CRITICAL ERROR: File {saved_path} does not exist after saving.")
        except Exception as e:
            logger.error(f"Error during dummy payload generation/saving: {e}", exc_info=True)

        logger.info(f"Available payloads from dummy generator: {generator.get_available_payloads()}")

    except Exception as e:
        logger.error(f"Error initializing or using PayloadGenerator: {e}", exc_info=True)

    # Clean up test directory
    if os.path.exists(test_output_dir):
        logger.info(f"Cleaning up test directory: {test_output_dir}")
        try:
            shutil.rmtree(test_output_dir)
            logger.info("Test directory removed successfully.")
        except Exception as e:
            logger.error(f"Error removing test directory {test_output_dir}: {e}", exc_info=True)

    logger.info("PayloadGenerator base class demonstration finished.")
