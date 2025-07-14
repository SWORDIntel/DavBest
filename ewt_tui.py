from textual.app import App, ComposeResult, RenderResult
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Header, Footer, Button, Static, Placeholder, Input, Label, Switch, LoadingIndicator, SelectionList, RichLog, DataTable
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
    from webdav_server import DAVServer
    from ewt_cli import generate_attack_package
    # We need a "dummy" config for WebDAVSecurityTester to initialize for get_all_available_tests
    # This config won't be used for actual connections, just for listing tests.
    temp_tester_config = {
        'webdav_url': 'http://dummy-url-for-listing.com', # Required but not used for test listing
        'output_dir': './ewt_tui_temp_output/payloads', # Ensure this is acceptable
        'report_dir': './ewt_tui_temp_output/reports'
    }
    # Create output directories if they don't exist
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
            Button("Vector Generator", id="vector_generator", variant="primary"),
            Button("WebDAV Server", id="webdav_server", variant="primary"),
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
        elif event.button.id == "vector_generator":
            self.app.push_screen(VectorGenScreen())
        elif event.button.id == "webdav_server":
            self.app.push_screen(DAVServerScreen())
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

class VectorGenScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(name="Vector Generation Wizard")
        with VerticalScroll(id="vector_gen_form"):
            yield Label("Payload Path:")
            yield Input(placeholder="/path/to/payload.exe", id="payload_path_input")
            yield Label("Decoy Document Path:")
            yield Input(placeholder="/path/to/decoy.pdf", id="decoy_path_input")
            yield Label("C2 Server URL (ip:port):")
            yield Input(placeholder="10.10.10.10:8080", id="c2_url_input")
            yield Button("Generate Package", id="generate_package_button", variant="success")
            yield RichLog(id="vector_gen_log", wrap=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate_package_button":
            payload_path = self.query_one("#payload_path_input", Input).value
            decoy_path = self.query_one("#decoy_path_input", Input).value
            c2_url = self.query_one("#c2_url_input", Input).value
            log_widget = self.query_one("#vector_gen_log", RichLog)
            log_widget.clear()

            if not all([payload_path, decoy_path, c2_url]):
                log_widget.write("[red]Error: All fields are required.[/red]")
                return

            log_widget.write("[yellow]Generating attack package...[/yellow]")

            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                generate_attack_package(payload_path, decoy_path, c2_url)
            output = f.getvalue()

            log_widget.write(output)

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
        yield Footer()

    def on_mount(self) -> None:
        """Fetch available tests when the screen is mounted."""
        self.run_worker(self._fetch_available_tests, thread=True)

    @work(thread=True)
    def _fetch_available_tests(self) -> None:
        """Worker to fetch available tests."""
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
        """Handle the message containing the available tests."""
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


class GenerateConfigScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back"), ("ctrl+s", "save_config_json", "Save JSON")]

    class AvailableTestsMessage(SelectTestsScreen.AvailableTestsMessage):
        pass

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._loading_indicator: LoadingIndicator | None = None
        self._available_tests_slist: SelectionList[str] | None = None
        self._configured_tests_table: DataTable[str] | None = None
        self._params_form_container: VerticalScroll | None = None
        self.configured_tests_data: list[dict] = []
        self._next_configured_test_unique_id = 0

    def compose(self) -> ComposeResult:
        yield Header(name="Generate Batch Configuration")
        with Horizontal(id="main_config_layout"):
            with VerticalScroll(id="available_tests_panel"):
                yield Static("Available Tests:", classes="panel_title")
                self._loading_indicator = LoadingIndicator()
                yield self._loading_indicator
                yield Button("Add to Batch >>", id="add_test_to_batch_button", variant="success")
            with VerticalScroll(id="configured_tests_panel"):
                yield Static("Tests in Batch:", classes="panel_title")
                self._configured_tests_table = DataTable(id="configured_tests_table")
                self._configured_tests_table.add_column("ID", key="uid")
                self._configured_tests_table.add_column("Test Type", key="test_id")
                yield self._configured_tests_table
                yield Button("Remove Selected from Batch", id="remove_test_from_batch_button", variant="error")
            with VerticalScroll(id="params_and_common_panel"):
                yield Static("Parameters for Selected Test:", classes="panel_title")
                self._params_form_container = VerticalScroll(id="params_form_container")
                yield self._params_form_container
                yield Static("Common Batch Settings:", classes="panel_title section_label")
                yield Input(placeholder="Default Callback URL (optional)", id="common_callback_url")
                yield Input(placeholder="Remote Target Directory (optional, e.g., my_batch_run)", id="common_remote_dir")
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
        available_tests_panel = self.query_one("#available_tests_panel")
        if self._loading_indicator:
            await self._loading_indicator.remove()
            self._loading_indicator = None
        if not message.tests:
            await available_tests_panel.mount(Static("No tests available.", id="no_avail_tests_message"))
            self.query_one("#add_test_to_batch_button", Button).disabled = True
            return
        selections = [Selection(test_id, test_id) for test_id in message.tests]
        self._available_tests_slist = SelectionList[str](*selections, id="available_tests_for_batch")
        await available_tests_panel.mount(self._available_tests_slist, before="#add_test_to_batch_button")

    def _add_selected_test_to_batch(self) -> None:
        if self._available_tests_slist and self._available_tests_slist.highlighted is not None:
            test_id_to_add = self._available_tests_slist.get_option_at_index(self._available_tests_slist.highlighted_row).value
            new_test_uid = self._next_configured_test_unique_id
            self._next_configured_test_unique_id += 1
            self.configured_tests_data.append({
                'uid': new_test_uid,
                'test_id': test_id_to_add,
                'params': {}
            })
            self._configured_tests_table.add_row(str(new_test_uid), test_id_to_add, key=str(new_test_uid))
            self.app.notify(f"Added '{test_id_to_add}' to batch.", timeout=2)
        else:
            self.app.notify("No test selected from available list.", severity="warning", timeout=3)

    def _remove_selected_test_from_batch(self) -> None:
        selected_row_key = self._configured_tests_table.cursor_coordinate.row_key
        if selected_row_key is not None:
            row_uid_str = str(selected_row_key.value)
            self.configured_tests_data = [
                test_item for test_item in self.configured_tests_data if str(test_item['uid']) != row_uid_str
            ]
            self._configured_tests_table.remove_row(selected_row_key)
            self.app.notify(f"Removed test with UID '{row_uid_str}' from batch.", timeout=2)
            self._clear_params_form()
        else:
            self.app.notify("No test selected in the batch table to remove.", severity="warning", timeout=3)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key_str = str(event.row_key.value)
        selected_test_data = next((item for item in self.configured_tests_data if str(item['uid']) == row_key_str), None)
        if selected_test_data:
            await self._populate_params_form(selected_test_data['test_id'], selected_test_data['params'])
        else:
            self._clear_params_form()

    async def _populate_params_form(self, test_id: str, current_params: dict) -> None:
        self._clear_params_form()
        if not _ewt_tester_for_listing: return

        file_type, payload_name = test_id.split('/', 1)
        param_definitions = []
        try:
            if file_type == "svg":
                param_definitions = _ewt_tester_for_listing.svg_generator.get_payload_params_definition(payload_name)
            elif file_type == "css":
                param_definitions = _ewt_tester_for_listing.css_generator.get_payload_params_definition(payload_name)
        except Exception as e:
            self.app.notify(f"Error getting params for {test_id}: {e}", severity="error")
            return

        if not param_definitions:
            await self._params_form_container.mount(Static("This test type requires no parameters."))
            return

        for p_def in param_definitions:
            param_label = Label(f"{p_def['label']} ({p_def['name']}):")
            param_input = Input(
                value=str(current_params.get(p_def['name'], p_def['default'])),
                placeholder=f"Default: {p_def['default']}",
                id=f"param_input_{test_id.replace('/','_')}_{p_def['name']}"
            )
            await self._params_form_container.mount(param_label, param_input)
            if p_def.get('description'):
                await self._params_form_container.mount(Static(f"  [dim]{p_def['description']}[/dim]"))

    def _clear_params_form(self) -> None:
        if self._params_form_container:
            self._params_form_container.remove_children()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_test_to_batch_button":
            self._add_selected_test_to_batch()
        elif event.button.id == "remove_test_from_batch_button":
            self._remove_selected_test_from_batch()

    def action_save_config_json(self) -> None:
        self.app.log("Save JSON action triggered.")
        if self._configured_tests_table.row_count > 0 and self._configured_tests_table.cursor_row >= 0:
            current_focused_row_key = self._configured_tests_table.get_row_at(self._configured_tests_table.cursor_row)[0]
            if current_focused_row_key is not None:
                focused_uid_str = str(current_focused_row_key)
                for test_data in self.configured_tests_data:
                    if str(test_data['uid']) == focused_uid_str:
                        self.app.log(f"Attempting to save params from form for test UID {focused_uid_str}, test_id {test_data['test_id']}")
                        current_params_from_form = {}
                        file_type, payload_name = test_data['test_id'].split('/',1)
                        param_defs = []
                        if _ewt_tester_for_listing:
                            if file_type == "svg":
                                param_defs = _ewt_tester_for_listing.svg_generator.get_payload_params_definition(payload_name)
                            elif file_type == "css":
                                param_defs = _ewt_tester_for_listing.css_generator.get_payload_params_definition(payload_name)
                        for p_def in param_defs:
                            param_input_id = f"#param_input_{test_data['test_id'].replace('/','_')}_{p_def['name']}"
                            try:
                                param_widget = self._params_form_container.query_one(param_input_id, Input)
                                current_params_from_form[p_def['name']] = param_widget.value
                            except Exception as e:
                                self.app.log(f"Could not find/query param input {param_input_id}: {e}")
                        test_data['params'] = current_params_from_form
                        self.app.log(f"Updated params for UID {focused_uid_str}: {current_params_from_form}")
                        break

        common_callback = self.query_one("#common_callback_url", Input).value or None
        common_remote_dir = self.query_one("#common_remote_dir", Input).value or None
        output_tests_list = []
        for configured_test in self.configured_tests_data:
            test_entry = {
                "file_type": configured_test["test_id"].split('/')[0],
                "payload_name": configured_test["test_id"].split('/')[1],
                "params": configured_test["params"]
            }
            if common_remote_dir:
                test_entry["remote_target_dir"] = common_remote_dir
            output_tests_list.append(test_entry)

        batch_config_to_save = {"tests": output_tests_list}
        if common_callback or common_remote_dir:
            batch_config_to_save["tui_common_settings"] = {
                "default_callback_url": common_callback,
                "common_remote_target_dir": common_remote_dir
            }
        output_filename = "ewt_batch_config.json"
        import json
        try:
            with open(output_filename, "w", encoding='utf-8') as f:
                json.dump(batch_config_to_save, f, indent=2)
            self.app.notify(f"Batch config saved to {output_filename}", severity="information", timeout=5)
            self.app.log(f"Batch config saved: {json.dumps(batch_config_to_save, indent=2)}")
        except Exception as e:
            self.app.notify(f"Error saving batch config: {e}", severity="error", timeout=10)
            self.app.log(f"Error saving batch config: {e}")

    def action_pop_screen(self) -> None:
        self.app.pop_screen()


class ViewReportsScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]
    REPORT_DIRS = ["./ewt_tui_output/reports/", "./ewt_output/reports/", "./reports/"]

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


class DAVServerScreen(Screen):
    BINDINGS = [("escape", "pop_screen", "Back")]

    class ServerStatusMessage(Message):
        def __init__(self, status: str, message: str) -> None:
            self.status = status
            self.message = message
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(name="WebDAV Server Control")
        with VerticalScroll(id="dav_server_config"):
            yield Label("Root Directory:")
            yield Input(value="./webdav_root", id="dav_root_dir")
            yield Label("Host IP:")
            yield Input(value="0.0.0.0", id="dav_host")
            yield Label("Port:")
            yield Input(value="8080", id="dav_port", validators=[Number(minimum=1, maximum=65535)])
            yield Horizontal(
                Button("Start Server", id="start_dav_server", variant="success"),
                Button("Stop Server", id="stop_dav_server", variant="error", disabled=True),
            )
            yield Static("Server Status: [bold red]Stopped[/bold red]", id="dav_server_status")
            yield RichLog(id="dav_server_log", wrap=True)
        yield Footer()

    @work(thread=True)
    def _start_server_worker(self, root_path: str, host: str, port: int) -> None:
        try:
            self.post_message(self.ServerStatusMessage("starting", f"Attempting to start server on {host}:{port}..."))
            self.app.dav_server_instance = DAVServer(root_path=root_path, host=host, port=port)
            self.post_message(self.ServerStatusMessage("started", f"Server running on http://{host}:{port}"))
            self.app.dav_server_instance.start()
            self.post_message(self.ServerStatusMessage("stopped", "Server has been stopped."))
        except Exception as e:
            self.post_message(self.ServerStatusMessage("error", f"Failed to start server: {e}"))
            self.app.dav_server_instance = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_dav_server":
            if self.app.dav_server_instance:
                self.app.notify("Server is already running.", severity="warning")
                return
            root_dir_widget = self.query_one("#dav_root_dir", Input)
            host_widget = self.query_one("#dav_host", Input)
            port_widget = self.query_one("#dav_port", Input)
            if not port_widget.is_valid:
                self.app.notify("Invalid port number.", severity="error")
                return
            root_path = root_dir_widget.value
            host = host_widget.value
            port = int(port_widget.value)
            self.run_worker(self._start_server_worker, root_path, host, port, exclusive=True)
            self.query_one("#start_dav_server", Button).disabled = True
            self.query_one("#stop_dav_server", Button).disabled = False
        elif event.button.id == "stop_dav_server":
            if self.app.dav_server_instance and self.app.dav_server_instance.server:
                self.app.dav_server_instance.server.stop()
                self.app.dav_server_instance = None
                self.query_one("#start_dav_server", Button).disabled = False
                self.query_one("#stop_dav_server", Button).disabled = True
                self.app.notify("Server stopped.")
            else:
                self.app.notify("Server is not running.", severity="warning")

    async def on_dav_server_screen_server_status_message(self, message: ServerStatusMessage) -> None:
        status_widget = self.query_one("#dav_server_status", Static)
        log_widget = self.query_one("#dav_server_log", RichLog)
        if message.status == "starting":
            status_widget.update("Server Status: [bold yellow]Starting...[/bold yellow]")
            log_widget.write(f"[yellow]{message.message}[/yellow]")
        elif message.status == "started":
            status_widget.update("Server Status: [bold green]Running[/bold green]")
            log_widget.write(f"[green]{message.message}[/green]")
        elif message.status == "stopped":
            status_widget.update("Server Status: [bold red]Stopped[/bold red]")
            log_widget.write(f"[red]{message.message}[/red]")
            self.query_one("#start_dav_server", Button).disabled = False
            self.query_one("#stop_dav_server", Button).disabled = True
        elif message.status == "error":
            status_widget.update("Server Status: [bold red]Error[/bold red]")
            log_widget.write(f"[bold red]{message.message}[/bold red]")
            self.query_one("#start_dav_server", Button).disabled = False
            self.query_one("#stop_dav_server", Button).disabled = True

    def action_pop_screen(self) -> None:
        if self.app.dav_server_instance:
            self.app.notify("Stopping WebDAV server before leaving screen.", severity="warning")
            self.app.dav_server_instance.server.stop()
            self.app.dav_server_instance = None
        self.app.pop_screen()


class EWTApp(App[None]):
    CSS_PATH = "ewt_tui.tcss"
    SCREENS = {"main_menu": MainMenuScreen}
    target_config: TargetConfig = TargetConfig()
    selected_tests: list[str] = []
    dav_server_instance: DAVServer | None = None

    def on_mount(self) -> None:
        self.push_screen("main_menu")

    def action_quit_app(self) -> None:
        if self.dav_server_instance:
            self.dav_server_instance.server.stop()
        self.exit()


if __name__ == "__main__":
    app = EWTApp()
    app.run()