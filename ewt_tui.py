from textual.app import App, ComposeResult, RenderResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, Placeholder, Input, Label, Switch, LoadingIndicator, SelectionList, RichLog
from textual.widgets.selection_list import Selection
from textual.screen import Screen
from textual.validation import Number
from textual.worker import get_current_worker # Worker class itself is not needed for @work
from textual import work # Correct import for @work decorator
from textual.message import Message

import datetime # For RunTestsScreen worker
import os # For path operations in ViewReportsScreen

# Attempt to import core components
try:
    from webdav_security_tester import WebDAVSecurityTester
    # We need a "dummy" config for WebDAVSecurityTester to initialize for get_all_available_tests
    # This config won't be used for actual connections, just for listing tests.
    temp_tester_config = {
        'webdav_url': 'http://dummy-url-for-listing.com', # Required but not used for test listing
        'output_dir': './ewt_tui_temp_output/payloads',
        'report_dir': './ewt_tui_temp_output/reports'
    }
    # Ensure output directories are created if the tester's __init__ does that.
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
            self.app.push_screen(RunTestsScreen())
        elif event.button.id == "view_reports":
            self.app.push_screen(ViewReportsScreen())
        elif event.button.id == "generate_config":
            self.app.push_screen(GenerateConfigScreen())
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
                self.app.target_config.timeout = 30.0
                if timeout_input.is_mounted:
                    timeout_input.value = "30.0"
                self.app.bell()

            self.app.target_config.verify_ssl = verify_ssl_switch.value

            self.app.notify("Configuration saved!", severity="information", timeout=3)
            self.app.pop_screen()

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

class GenerateConfigScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back"), ("ctrl+s", "save_config_json", "Save JSON")]

    class AvailableTestsMessage(Message):
        """Message to pass available tests from worker to screen."""
        def __init__(self, tests: list[str]) -> None:
            self.tests = tests
            super().__init__()

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._loading_indicator: LoadingIndicator | None = None
        self._available_tests_list: SelectionList[str] | None = None
        self.selected_batch_tests: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(name="Generate Batch Configuration")
        self._loading_indicator = LoadingIndicator()
        yield self._loading_indicator
        yield Static("Select tests to add to batch configuration:", classes="section_label")
        yield Static("TODO: Add area for selected tests, parameters, common settings, and save button.", classes="placeholder_text")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._fetch_available_tests_for_batch, thread=True)

    @work(thread=True)
    def _fetch_available_tests_for_batch(self) -> None:
        worker = get_current_worker()
        if not worker.is_cancelled:
            if _ewt_tester_for_listing:
                try:
                    available_tests = _ewt_tester_for_listing.get_all_available_tests()
                    self.post_message(GenerateConfigScreen.AvailableTestsMessage(available_tests))
                except Exception as e:
                    self.app.notify(f"Error fetching tests: {e}", severity="error", timeout=10)
                    self.post_message(GenerateConfigScreen.AvailableTestsMessage([]))
            else:
                self.app.notify("Test runner not available for listing tests.", severity="error", timeout=5)
                self.post_message(GenerateConfigScreen.AvailableTestsMessage([]))

    async def on_generate_config_screen_available_tests_message(self, message: AvailableTestsMessage) -> None:
        if self._loading_indicator:
            await self._loading_indicator.remove()
            self._loading_indicator = None

        if not message.tests:
            no_tests_static = Static("No tests available to select.", id="no_avail_tests_message")
            await self.mount(no_tests_static, after=self.query_one(".section_label", Static))
            return

        selections = [Selection(test_id, test_id) for test_id in message.tests]
        self._available_tests_list = SelectionList[str](*selections, id="available_tests_for_batch")
        await self.mount(self._available_tests_list, after=self.query_one(".section_label", Static))

    def action_save_config_json(self) -> None:
        self.app.notify("Save JSON action triggered (not yet implemented).", severity="warning")

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

class ViewReportsScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    REPORT_DIRS = [
        "./ewt_tui_output/reports/",
        "./ewt_output/reports/",
        "./reports/"
    ]

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._report_files_list: SelectionList[str] | None = None
        self._loading_indicator: LoadingIndicator | None = None

    def compose(self) -> ComposeResult:
        yield Header(name="View Reports")
        self._loading_indicator = LoadingIndicator()
        yield self._loading_indicator
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._scan_report_dirs, thread=True)

    @work(thread=True)
    def _scan_report_dirs(self) -> None:
        report_files = []
        checked_dirs_messages = []

        for rep_dir in self.REPORT_DIRS:
            abs_rep_dir = os.path.abspath(rep_dir)
            checked_dirs_messages.append(f"Checking: {abs_rep_dir}")
            if os.path.isdir(abs_rep_dir):
                try:
                    for item in os.listdir(abs_rep_dir):
                        if item.endswith(".md") and os.path.isfile(os.path.join(abs_rep_dir, item)):
                            report_files.append(os.path.join(abs_rep_dir, item))
                except OSError as e:
                    checked_dirs_messages.append(f"  Error accessing {abs_rep_dir}: {e}")
            else:
                checked_dirs_messages.append(f"  Directory not found: {abs_rep_dir}")

        self.app.call_from_thread(self._update_report_list, report_files, checked_dirs_messages)

    async def _update_report_list(self, report_files: list[str], checked_dirs_messages: list[str]):
        if self._loading_indicator:
            await self._loading_indicator.remove()
            self._loading_indicator = None

        if not report_files:
            await self.mount(Static("No Markdown reports found in checked directories.", id="no_reports_message"))
        else:
            unique_reports = sorted(list(set(report_files)), key=os.path.basename)

            selections = [
                Selection(
                    prompt=f"{os.path.basename(path)} ({os.path.dirname(path)})",
                    value=path,
                    id=f"report_{i}"
                ) for i, path in enumerate(unique_reports)
            ]
            self._report_files_list = SelectionList[str](*selections, id="report_files_list")
            await self.mount(self._report_files_list)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

class SelectTestsScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back"), ("s", "save_selection", "Save")]

    class AvailableTestsMessage(Message):
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
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._fetch_available_tests, thread=True)

    @work(thread=True)
    def _fetch_available_tests(self) -> None:
        worker = get_current_worker()
        if not worker.is_cancelled:
            if _ewt_tester_for_listing:
                try:
                    available_tests = _ewt_tester_for_listing.get_all_available_tests()
                    self.post_message(self.AvailableTestsMessage(available_tests))
                except Exception as e:
                    self.app.notify(f"Error fetching tests: {e}", severity="error", timeout=10)
                    self.post_message(self.AvailableTestsMessage([]))
            else:
                self.app.notify("Test runner not available.", severity="error", timeout=5)
                self.post_message(self.AvailableTestsMessage([]))

    async def on_select_tests_screen_available_tests_message(self, message: AvailableTestsMessage) -> None:
        if self._loading_indicator:
            await self._loading_indicator.remove()
            self._loading_indicator = None

        if not message.tests:
            await self.mount(Static("No tests available or error loading tests.", id="no_tests_message"))
            return

        selections = []
        for test_id_str in message.tests:
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

class RunTestsScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    class TestStatusMessage(Message):
        def __init__(self, line: str) -> None:
            self.line = line
            super().__init__()

    class AllTestsCompleteMessage(Message):
        def __init__(self, final_report_path: str | None) -> None:
            self.final_report_path = final_report_path
            super().__init__()

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._log_widget: RichLog | None = None
        self._start_button: Button | None = None
        self._is_running_tests = False

    def compose(self) -> ComposeResult:
        yield Header(name="Run Tests")
        self._start_button = Button("Start Selected Tests", id="start_tests_button", variant="success")
        yield self._start_button
        self._log_widget = RichLog(id="test_run_log", wrap=True, highlight=True, markup=True)
        yield self._log_widget
        yield Footer()

    def on_mount(self) -> None:
        if not self.app.selected_tests:
            self._log_widget.write("[yellow]No tests selected. Please go to 'Select Tests' first.[/yellow]")
            self._start_button.disabled = True
        elif not self.app.target_config.url:
            self._log_widget.write("[yellow]Target URL not configured. Please go to 'Configure Target' first.[/yellow]")
            self._start_button.disabled = True
        else:
            self._log_widget.write(f"Ready to run {len(self.app.selected_tests)} selected tests on [blue]{self.app.target_config.url}[/blue].")
            self._log_widget.write("Press 'Start Selected Tests' to begin.")

    @work(thread=True)
    def _execute_tests_worker(self) -> None:
        if _ewt_tester_for_listing is None:
            self.post_message(self.TestStatusMessage("[bold red]Error: Core testing module not loaded.[/bold red]"))
            self.post_message(self.AllTestsCompleteMessage(None))
            return

        try:
            current_target_config = {
                'webdav_url': self.app.target_config.url,
                'username': self.app.target_config.username,
                'password': self.app.target_config.password,
                'timeout': self.app.target_config.timeout,
                'verify_ssl': self.app.target_config.verify_ssl,
                'output_dir': './ewt_tui_output/payloads',
                'report_dir': './ewt_tui_output/reports',
                'log_level': "INFO"
            }
            os.makedirs(current_target_config['output_dir'], exist_ok=True)
            os.makedirs(current_target_config['report_dir'], exist_ok=True)

            tester = WebDAVSecurityTester(config=current_target_config)

            self.post_message(self.TestStatusMessage(f"[cyan]Initializing test run against {tester.config['webdav_url']}...[/cyan]"))

            tests_to_run_configs = []
            for test_id_str in self.app.selected_tests:
                file_type, payload_name = test_id_str.split('/', 1)
                tests_to_run_configs.append({
                    'file_type': file_type,
                    'payload_name': payload_name,
                    'params': {}
                })

            if not tests_to_run_configs:
                self.post_message(self.TestStatusMessage("[yellow]No tests to run based on selection.[/yellow]"))
                self.post_message(self.AllTestsCompleteMessage(None))
                return

            total_tests = len(tests_to_run_configs)
            for i, test_config in enumerate(tests_to_run_configs):
                self.post_message(self.TestStatusMessage(
                    f"[magenta]Running test {i+1}/{total_tests}: {test_config['file_type']}/{test_config['payload_name']}...[/magenta]"
                ))
                try:
                    result = tester.run_test(
                        file_type=test_config['file_type'],
                        payload_name=test_config['payload_name'],
                        params=test_config.get('params', {}),
                        remote_target_dir=f"ewt_tui_run_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    status_color = "green" if result['status'] == 'SUCCESS' else "red"
                    self.post_message(self.TestStatusMessage(
                        f"  Result: [{status_color}]{result['status']}[/{status_color}] - "
                        f"Upload: {result['upload_success']}, Verify: {result['verify_get_success']}, Match: {result['content_match']}"
                    ))
                    if result.get('error_message'):
                         self.post_message(self.TestStatusMessage(f"  [yellow]Details: {result['error_message']}[/yellow]"))

                except Exception as e:
                    self.post_message(self.TestStatusMessage(f"  [bold red]Error running test {test_config['file_type']}/{test_config['payload_name']}: {e}[/bold red]"))

            self.post_message(self.TestStatusMessage("[cyan]All selected tests processed. Generating report...[/cyan]"))
            report_path = tester.generate_report(report_filename_base="EWT_TUI_Report")
            self.post_message(self.AllTestsCompleteMessage(report_path))

        except Exception as e:
            self.app.notify(f"Worker error: {e}", severity="error", timeout=10)
            self.post_message(self.TestStatusMessage(f"[bold red]Critical error in test worker: {e}[/bold red]"))
            self.post_message(self.AllTestsCompleteMessage(None))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_tests_button" and not self._is_running_tests:
            if not self.app.selected_tests or not self.app.target_config.url:
                self.app.notify("Configuration or test selection is missing.", severity="error", timeout=5)
                return

            self._is_running_tests = True
            self._start_button.disabled = True
            self._log_widget.clear()
            self._log_widget.write("[cyan]Starting test execution...[/cyan]")
            self.run_worker(self._execute_tests_worker, exclusive=True)

    async def on_run_tests_screen_test_status_message(self, message: TestStatusMessage) -> None:
        if self._log_widget:
            self._log_widget.write(message.line)

    async def on_run_tests_screen_all_tests_complete_message(self, message: AllTestsCompleteMessage) -> None:
        if self._log_widget:
            if message.final_report_path:
                self._log_widget.write(f"[bold green]All tests complete! Report generated: {message.final_report_path}[/bold green]")
            else:
                self._log_widget.write("[bold red]All tests complete, but report generation failed or was skipped.[/bold red]")
        if self._start_button:
            self._start_button.disabled = False
        self._is_running_tests = False
        self.app.notify("Test run finished.", severity="information", timeout=5)

    def action_pop_screen(self) -> None:
        if self._is_running_tests:
            self.app.notify("Tests are currently running.", severity="warning", timeout=3)
            return
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
    selected_tests: list[str] = []

    def on_mount(self) -> None:
        self.push_screen("main_menu")

    def action_quit_app(self) -> None:
        self.exit()

if __name__ == "__main__":
    app = EWTApp()
    async def run_test():
        async with app.run_test(headless=True, size=(100, 40)) as pilot:
            await pilot.pause(0.1)

            # 1. Test Configure Target Screen
            await pilot.press("enter")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, ConfigureTargetScreen), "ConfigureTargetScreen not active"
            
            def set_value_and_save():
                config_screen = app.screen
                if isinstance(config_screen, ConfigureTargetScreen):
                    url_input = config_screen.query_one("#url_input", Input)
                    url_input.value = "http://configured.test.com"
                    config_screen.query_one("#save_config", Button).press()
            app.call_later(set_value_and_save)
            await pilot.pause(0.2)
            await pilot.wait_for_animation()
            
            assert app.target_config.url == "http://configured.test.com"
            assert isinstance(app.screen, MainMenuScreen), "Not back to MainMenu after config save"

            # 2. Test Select Tests Screen
            await pilot.click("#select_tests")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, SelectTestsScreen), f"SelectTestsScreen not active. Currently: {app.screen}"
            await pilot.pause(0.5)

            try:
                selection_list = app.screen.query_one(SelectionList)
                if selection_list.option_count > 0:
                    await pilot.press("enter")
                    app.selected_tests = list(selection_list.selected)
            except Exception as e:
                print(f"Warning: Test selection interaction failed: {e}")

            await pilot.press("s")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, MainMenuScreen), f"Not back to MainMenu after test selection. Currently: {app.screen}"

            # 3. Navigate to Run Tests Screen
            await pilot.click("#run_tests")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, RunTestsScreen), f"RunTestsScreen not active. Currently: {app.screen}"
            await pilot.pause(0.2)
            
            start_button = app.screen.query_one("#start_tests_button", Button)
            if not start_button.disabled:
                await pilot.click("#start_tests_button")
                await pilot.pause(1.0)

            await pilot.press("escape")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, MainMenuScreen), f"Not back to MainMenu after escaping RunTestsScreen. Currently: {app.screen}"

            # 4. Navigate to View Reports Screen
            await pilot.click("#view_reports")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, ViewReportsScreen), f"ViewReportsScreen not active. Currently: {app.screen}"
            await pilot.pause(0.5)

            await pilot.press("escape")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, MainMenuScreen), f"Not back to MainMenu after escaping ViewReportsScreen. Currently: {app.screen}"
            
            # 5. Navigate to Generate Config Screen
            await pilot.click("#generate_config")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, GenerateConfigScreen), f"GenerateConfigScreen not active. Currently: {app.screen}"
            await pilot.pause(0.5)
            
            await pilot.press("escape")
            await pilot.wait_for_animation()
            assert isinstance(app.screen, MainMenuScreen), f"Not back to MainMenu after escaping GenerateConfigScreen. Currently: {app.screen}"

            # 6. Quit
            await pilot.press("q")
            await pilot.pause(0.1)

    import asyncio
    asyncio.run(run_test())
    print("TUI auto_pilot test with navigation to all main screens completed.")