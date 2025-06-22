from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, Placeholder, Input, Label, Switch
from textual.screen import Screen
from textual.validation import Number

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
            self.app.push_screen(PlaceholderScreen(title="Select Tests"))
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
    CSS_PATH = "ewt_tui.tcss" # Using an external CSS file now
    SCREENS = {"main_menu": MainMenuScreen}

    target_config: TargetConfig = TargetConfig() # App-level storage for config

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
            # Basic check: ensure the app starts and quits without error
            await pilot.pause(0.1)
            # Navigate to config screen
            await pilot.press("enter") # Press "Configure Target"
            await pilot.wait_for_animation() # Wait for screen transition

            # Ensure the ConfigureTargetScreen is active
            assert isinstance(app.screen, ConfigureTargetScreen), "ConfigureTargetScreen not active"

            # Interact with some fields (basic check)
            # Query within the currently active screen for robustness
            url_input_widget = app.screen.query_one("#url_input", Input)
            url_input_widget.value = "http://test.com"
            await pilot.pause(0.1) # Allow value propagation if needed

            # Assuming the "Save Configuration" button is the next focusable or directly press it by ID
            # For simplicity, let's assume pressing Enter on an input might eventually hit Save
            # or we can target the button directly if we know its position or make it default.
            # A more robust way would be to navigate to the button and press it.
            # For now, let's try to click the save button.
            # Textual's pilot can click buttons by CSS selector:
            await pilot.click("#save_config")
            await pilot.pause(0.1)
            # Go back to main or quit
            await pilot.press("escape") # Back to main menu
            await pilot.pause(0.1)
            await pilot.press("q") # Quit
            await pilot.pause(0.1)

    import asyncio
    asyncio.run(run_test())
    print("TUI basic auto_pilot test with navigation to config screen completed.")
