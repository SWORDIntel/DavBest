from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Static, Placeholder
from textual.screen import Screen

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
            self.app.push_screen(PlaceholderScreen(title="Configure Target"))
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


class EWTApp(App):
    CSS = """
    #main_menu_buttons {
        align: center middle;
        padding: 2;
    }
    #main_menu_buttons Button {
        width: 80%;
        margin: 1;
    }
    #placeholder_content {
        align: center middle;
        padding: 2;
    }
    """
    SCREENS = {"main_menu": MainMenuScreen}

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
        async with app.run_test(headless=True, size=(80, 24)) as pilot:
            # Basic check: ensure the app starts and quits without error
            await pilot.pause(0.1) # Give it a moment to initialize
            # You could add pilot.press("q") here if needed,
            # but exit() should be called by action_quit_app or direct exit.
            # For now, just ensuring it starts and can be exited is enough.
            pass

    import asyncio
    asyncio.run(run_test())
    print("TUI basic auto_pilot test completed without crashing.")
