from textual.app import App, ComposeResult, RenderResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, Placeholder, Input, Label, Switch, LoadingIndicator, SelectionList
from textual.widgets.selection_list import Selection
from textual.screen import Screen
from textual.validation import Number
from textual.worker import get_current_worker # Worker class itself is not needed for @work
from textual import work # Correct import for @work decorator
from textual.message import Message

# Attempt to import core components
try:
    from webdav_security_tester import WebDAVSecurityTester
    # We need a "dummy" config for WebDAVSecurityTester to initialize for get_all_available_tests
    # This config won't be used for actual connections, just for listing tests.
    # Output dirs might be created, so use a temporary or controllable path if needed.
    # For simplicity here, we assume default paths are okay or will be handled/ignored.
    temp_tester_config = {
        'webdav_url': 'http://dummy-url-for-listing.com', # Required but not used for test listing
        'output_dir': './ewt_tui_temp_output/payloads', # Ensure this is acceptable
        'report_dir': './ewt_tui_temp_output/reports'   # Ensure this is acceptable
    }
    # Create a global instance for fetching tests, or create it on demand.
    # Creating it on demand within the worker might be cleaner if config can change.
    # For now, let's assume it's okay to instantiate it once for test listing.
    # Ensure output directories are created if the tester's __init__ does that.
    import os
    os.makedirs(temp_tester_config['output_dir'], exist_ok=True)
    os.makedirs(temp_tester_config['report_dir'], exist_ok=True)

    # This instance is SOLELY for get_all_available_tests.
    # Actual test runs will use the TargetConfig from the UI.
    _ewt_tester_for_listing = WebDAVSecurityTester(config=temp_tester_config)
except ImportError:
    _ewt_tester_for_listing = None
    print("Error: webdav_security_tester.py not found or WebDAVSecurityTester could not be imported.")
    print("Test selection screen will be empty.")


class TargetConfig:
    def __init__(self):
        self.url: str = ""
        self.username: str | None = None
        self.password: str | None = None
        self.timeout: float = 30.0
        self.verify_ssl: bool = True

class MainMenuScreen(Screen):
    BINDINGS = [("q", "quit_app", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(name="Enhanced WebDAV Security Tester")
        yield Container(
            Button("Configure Target", id="configure_target", variant="primary"),
            Button("Select Tests", id="select_tests", variant="primary"),
            Button("Run Tests", id="run_tests", variant="primary"),
            Button("View Reports", id="view_reports", variant="primary"),
            Button("Generate Config", id="generate_config", variant="primary"),
            Button("Quit", id="quit_app_button", variant="error"),
            id="main_menu_buttons"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "configure_target":
            self.app.push_screen(ConfigureTargetScreen())
        elif event.button.id == "select_tests":
            self.app.push_screen(SelectTestsScreen())
        elif event.button.id == "run_tests":
            self.app.push_screen(PlaceholderScreen(title="Run Tests"))
        elif event.button.id == "view_reports":
            self.app.push_screen(PlaceholderScreen(title="View Reports"))
        elif event.button.id == "generate_config":
            self.app.push_screen(PlaceholderScreen(title="Generate Configuration"))
        elif event.button.id == "quit_app_button":
            self.app.action_quit_app()

    def action_quit_app(self) -> None:
        self.app.exit()

class ConfigureTargetScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(name="Configure Target Server")
        with VerticalScroll(id="config_form"):
            yield Label("WebDAV URL:")
            yield Input(
                placeholder="https://example.com/webdav",
                id="url_input",
                value=self.app.target_config.url
            )
            yield Label("Username (optional):")
            yield Input(
                placeholder="user",
                id="username_input",
                value=self.app.target_config.username or ""
            )
            yield Label("Password (optional):")
            yield Input(
                placeholder="password",
                password=True,
                id="password_input",
                value=self.app.target_config.password or ""
            )
            yield Label("Timeout (seconds):")
            yield Input(
                placeholder="30.0",
                id="timeout_input",
                validators=[Number(minimum=1.0)],
                value=str(self.app.target_config.timeout)
            )
            yield Static("Verify SSL Certificate:")
            yield Switch(id="verify_ssl_switch", value=self.app.target_config.verify_ssl)
            yield Button("Save Configuration", id="save_config", variant="success")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_config":
            # Update the app's target_config object
            url_input = self.query_one("#url_input", Input)
            username_input = self.query_one("#username_input", Input)
            password_input = self.query_one("#password_input", Input)
            timeout_input = self.query_one("#timeout_input", Input)
            verify_ssl_switch = self.query_one("#verify_ssl_switch", Switch)

            self.app.target_config.url = url_input.value
            self.app.target_config.username = username_input.value if username_input.value else None
            self.app.target_config.password = password_input.value if password_input.value else None

            try:
                self.app.target_config.timeout = float(timeout_input.value)
            except ValueError:
                self.app.target_config.timeout = 30.0 # Default back if invalid
                timeout_input.value = "30.0" # Reflect default in UI
                self.app.bell() # Notify user of change
                self.app.notify("Invalid timeout value. Reset to default.", severity="warning", timeout=5)


            self.app.target_config.verify_ssl = verify_ssl_switch.value

            self.app.notify("Configuration saved!", severity="information", timeout=3)
            self.app.pop_screen()


    def action_pop_screen(self) -> None:
        self.app.pop_screen()

class SelectTestsScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back"), ("s", "save_selection", "Save")]

    class AvailableTestsMessage(Message):
        """Message to pass available tests from worker to screen."""
        def __init__(self, tests: list[str]) -> None:
            self.tests = tests
            super().__init__()

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._loading_indicator: LoadingIndicator | None = None
        self._selection_list: SelectionList[str] | None = None

    def compose(self) -> ComposeResult:
        yield Header(name="Select Tests")
        self._loading_indicator = LoadingIndicator()
        yield self._loading_indicator
        # SelectionList will be added here once tests are loaded
        yield Footer()

    def on_mount(self) -> None:
        """Fetch available tests when the screen is mounted."""
        self.run_worker(self._fetch_available_tests, thread=True) # thread=True is important for blocking IO

    @work(thread=True) # Corrected decorator and ensuring it runs in a thread
    def _fetch_available_tests(self) -> None:
        """Worker to fetch available tests."""
        worker = get_current_worker() # Get the worker instance
        if not worker.is_cancelled:  # Check if the worker has been cancelled
            if _ewt_tester_for_listing:
                try:
                    # Simulate some work / potential IO delay
                    # import time
                    # time.sleep(0.2) # Simulate network/processing delay
                    available_tests = _ewt_tester_for_listing.get_all_available_tests()
                    self.post_message(self.AvailableTestsMessage(available_tests))
                except Exception as e:
                    self.app.notify(f"Error fetching tests: {e}", severity="error", timeout=10)
                    self.post_message(self.AvailableTestsMessage([])) # Send empty list on error
            else:
                self.app.notify("Test runner not available.", severity="error", timeout=5)
                self.post_message(self.AvailableTestsMessage([])) # Send empty list

    async def on_select_tests_screen_available_tests_message(self, message: AvailableTestsMessage) -> None:
        """Handle the message containing the available tests."""
        if self._loading_indicator:
            await self._loading_indicator.remove()
            self._loading_indicator = None

        if not message.tests:
            await self.mount(Static("No tests available or error loading tests.", id="no_tests_message"))
            return

        selections = []
        for test_id_str in message.tests:
            # Check if this test was previously selected
            is_selected = test_id_str in self.app.selected_tests
            selections.append(Selection(test_id_str, test_id_str, is_selected))

        self._selection_list = SelectionList[str](*selections, id="test_selection_list")
        await self.mount(self._selection_list)


    def action_save_selection(self) -> None:
        if self._selection_list:
            self.app.selected_tests = list(self._selection_list.selected)
            self.app.notify(f"{len(self.app.selected_tests)} tests selected.", severity="information", timeout=3)
        self.app.pop_screen()

    def action_pop_screen(self) -> None:
        self.app.pop_screen()


class PlaceholderScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    def __init__(self, title: str, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self.title = title

    def compose(self) -> ComposeResult:
        yield Header(name=self.title)
        yield Container(
            Static(f"This is the '{self.title}' screen. Press ESC to go back."),
            Placeholder(label="Content Area"),
            id="placeholder_content"
        )
        yield Footer()

    def action_pop_screen(self) -> None:
        self.app.pop_screen()


class EWTApp(App[None]):
    CSS_PATH = "ewt_tui.tcss"
    SCREENS = {"main_menu": MainMenuScreen}

    target_config: TargetConfig = TargetConfig()
    selected_tests: list[str] = [] # Store IDs of selected tests

    def on_mount(self) -> None:
        self.push_screen("main_menu")

    def action_quit_app(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = EWTApp()
    # To perform a basic startup test when running the script directly:
    # app.run()

    # For a quick automated check:
    async def run_test():
        async with app.run_test(headless=True, size=(100, 40)) as pilot: # Increased height
            await pilot.pause(0.1) # App mount

            # 1. Test Configure Target Screen
            await pilot.press("enter") # Press "Configure Target"
            await pilot.wait_for_animation()
            assert isinstance(app.screen, ConfigureTargetScreen), "ConfigureTargetScreen not active"

            # Focus the URL input field first. We assume it's the first focusable input.
            # If not, we might need to navigate to it.


            url_input_widget_for_assertion = app.screen.query_one("#url_input", Input) # For final assertion check

            def set_value_via_call_later():
                # Query for the widget again inside call_later to ensure we have the right context
                input_widget_on_screen = app.screen.query_one("#url_input", Input)
                input_widget_on_screen.value = "http://configured.test.com"

            app.call_later(set_value_via_call_later)
            await pilot.pause() # Wait for call_later to execute and for the UI to idle

            await pilot.click("#save_config")
            await pilot.wait_for_animation() # Wait for pop_screen
            assert app.target_config.url == "http://configured.test.com", f"Config not saved. Expected 'http://configured.test.com', got '{app.target_config.url}' (Pilot's ref value was '{url_input_widget_for_assertion.value}')"
            assert isinstance(app.screen, MainMenuScreen), "Not back to MainMenu after config save"

            # 2. Test Select Tests Screen
            # Navigate to "Select Tests" - assuming it's the second button, requires navigating
            await pilot.press("down") # Focus "Select Tests"
            await pilot.press("enter") # Press "Select Tests"
            await pilot.wait_for_animation()
            assert isinstance(app.screen, SelectTestsScreen), "SelectTestsScreen not active"

            # Wait for tests to load (SelectionList to appear)
            # This is a bit tricky with headless; we might need a more robust wait
            # For now, a short pause and check if SelectionList is there.
            await pilot.pause(0.5) # Give worker time to load tests

            try:
                selection_list = app.screen.query_one(SelectionList)
                if selection_list.option_count > 0: # Assuming _ewt_tester_for_listing has tests
                    # Select the first test if available
                    await pilot.press("enter") # Toggle selection of the first item
                    await pilot.pause(0.1)
            except Exception as e:
                print(f"Warning: Test selection interaction failed in auto_pilot: {e}")
                # This might happen if _ewt_tester_for_listing failed or has no tests.
                # The test should still proceed to check if save/back works.

            await pilot.press("s") # Save selection
            await pilot.wait_for_animation()
            assert isinstance(app.screen, MainMenuScreen), "Not back to MainMenu after test selection"
            # We could also check app.selected_tests here if we knew what to expect

            # 3. Quit
            await pilot.press("q")
            await pilot.pause(0.1)

    import asyncio
    asyncio.run(run_test())
    print("TUI basic auto_pilot test with navigation to config and select tests screen completed.")
