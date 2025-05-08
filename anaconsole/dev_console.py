import time
import pygame as pg
import os
import inspect
from typing import get_type_hints, TYPE_CHECKING, Callable, Any
from itertools import islice
import types
import sys
from collections import deque
from .dev_overlay_element import DeveloperOverlayElement
from .button import Button
from .input_box import InputBox, Autocomplete
from .variable_monitor import VariableMonitorWindow
from pathlib import Path
import traceback
from .assets import load_file_stream
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay


CommandCarrierType = Any  # Any namespace that contains console commands


class OutputRedirector:
    stdout = sys.stdout

    def __init__(self, *custom_redirects: Callable[[str], None]):
        self.custom_redirects: tuple[Callable[[str], None], ...] = custom_redirects

    def write(self, text):
        self.stdout.write(text)
        if text.strip():  # Ignore empty lines
            for redirect in self.custom_redirects:
                redirect(text)

    def flush(self):
        self.stdout.flush()


def console_command(*aliases: str, is_cheat_protected: bool = False, show_return_value: bool = False, autocomplete_function: Callable[[str], tuple[int, list["Autocomplete.Option"]]] | None = None, hint: Callable[[CommandCarrierType], Any] | None = None):
    # This cursed if statement ensures that the decorator works even when used without parentheses
    if len(aliases) == 1 and callable(aliases[0]) and not isinstance(aliases[0], str):
        f = aliases[0]
        f._is_console_command = True
        return f

    def decorator(func):
        func._is_console_command = True
        func._aliases = aliases
        func._is_cheat_protected = is_cheat_protected
        func._show_return_value = show_return_value
        func._autocomplete_function = autocomplete_function
        if hint: setattr(func, "_hint", hint)
        return func
    return decorator


class Logger:
    def __init__(self,
                 screen_surface: pg.Surface,
                 max_relative_height: float = 0.3,
                 *,
                 font_override: pg.font.Font | None = None
                 ):
        self.font: pg.font.Font = font_override or pg.font.Font(load_file_stream("trebuc.ttf"), 18)
        max_lines = int(screen_surface.get_height() * max_relative_height / self.font.get_height())

        self.surface = pg.Surface((screen_surface.get_width(), max_lines * self.font.get_height()), flags=pg.SRCALPHA)
        self.surface.fill((0, 0, 0, 0))

        self.max_alpha: int = 200
        self.fade_start_time = 5.0
        self.fade_duration = 2.0

        self.log: deque[tuple[str, float]] = deque((("", 0.0) for _ in range(max_lines)), maxlen=max_lines)

    def print(self, text: str):
        self.log.append((text, time.time()))

    def render(self, surface: pg.Surface):
        self.surface.fill((0, 0, 0, 0))
        current_time: float = time.time()
        for i, (text, timestamp) in enumerate(reversed(self.log)):
            age: float = current_time - timestamp
            if age > self.fade_start_time + self.fade_duration:
                continue
            if age > self.fade_start_time:
                alpha = int(pg.math.lerp(self.max_alpha, 0.0, (age - self.fade_start_time) / self.fade_duration))
            else:
                alpha = self.max_alpha
            font_surface = self.font.render(text, True, (255, 255, 255))
            font_surface.set_alpha(alpha)
            self.surface.blit(font_surface, (0, self.surface.get_height() - (i+1) * font_surface.get_height()))
        surface.blit(self.surface, (0, surface.get_height() - self.surface.get_height()))


class DeveloperConsole(DeveloperOverlayElement):
    DEFAULT_HEIGHT = 200
    SUBMIT_BUTTON_WIDTH = 50

    def __init__(self, overlay: "DeveloperOverlay"):
        super().__init__(overlay, overlay, pg.Rect(0, 0, overlay.rect.w, self.DEFAULT_HEIGHT))

        input_box_height = int(overlay.char_height * 1.5)
        log_width = overlay.rect.w - 2 * overlay.border_offset
        input_box_width = log_width - overlay.border_offset - self.SUBMIT_BUTTON_WIDTH
        max_log_height = overlay.rect.w - input_box_height - 3 * overlay.border_offset

        # self.autocomplete = Autocomplete(overlay, (0, 0))
        self.input_box = InputBox(overlay, self, pg.Rect(self.overlay.border_offset,
                                                         self.surface.get_height() - input_box_height - self.overlay.border_offset,
                                                         input_box_width,
                                                         input_box_height),
                                  setter=self.handle_command,
                                  clear_on_send=True,
                                  lose_focus_on_send=False,
                                  autocomplete_function=self.dev_console_autocomplete,
                                  )
        self.log = Log(overlay, self, pg.Rect(self.overlay.border_offset,
                                              self.surface.get_height() - self.input_box.surface.get_height() - self.overlay.border_offset,
                                              log_width,
                                              max_log_height))

        submit_button = Button(overlay, self, pg.Rect(self.rect.right - self.SUBMIT_BUTTON_WIDTH - overlay.border_offset,
                                                      self.input_box.rect.top,
                                                      self.SUBMIT_BUTTON_WIDTH,
                                                      self.input_box.rect.h),
                               self.input_box.enter, image=overlay.font2.render("Submit", False, overlay.PRIMARY_TEXT_COLOR, overlay.PRIMARY_COLOR))
        self.children.append(self.input_box)
        self.children.append(submit_button)

        # self._namespace: types.SimpleNamespace = self._setup_namespace()  # Used for exec and eval commands

    def dev_console_autocomplete(self, text: str) -> tuple[int, list["Autocomplete.Option"]]:
        if not text:
            return 0, []
        words = text.split(" ", maxsplit=1)
        if len(words) == 1:
            position, options = 0, []
            for command, func in self.get_all_commands().items():
                command: str
                if not command.startswith(text) or command == text:
                    continue
                retrieved_value = None
                if hint := getattr(func, "_hint", None):
                    for command_carrier in self.overlay.namespace.__dict__.values():
                        try:
                            retrieved_value = hint(command_carrier)
                            break
                        except AttributeError:
                            continue
                options.append(Autocomplete.Option(command + " ", str(retrieved_value) if retrieved_value is not None else "", False))
            return position, options
        elif len(words) > 1:
            position = len(words[0]) + 1
            command: Callable[[...], Any] | None = self.get_all_commands().get(words[0])
            if not command:
                return 0, []
            autocomplete_function: Callable[[str], list[str]] | None = getattr(command, "_autocomplete_function", None)
            if not autocomplete_function:
                return 0, []
            for command_carrier in self.overlay.namespace.__dict__.values():
                if getattr(command_carrier, autocomplete_function.__name__, None):
                    offset, options = getattr(command_carrier, autocomplete_function.__name__)(words[1])
                    break
            position += offset
            return position, options

    def print_exception_to_log(self, e: Exception) -> None:
        self.log.print(f"{e.__class__.__name__}: {str(e)}", color=self.overlay.ERROR_COLOR,
                       mirror_to_stdout=True)
        for line in traceback.format_exc().split("\n"):
            self.log.print(line, color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)

    def exec_cfg_autocomplete(self, text: str) -> tuple[int, list["Autocomplete.Option"]]:
        directory = Path.cwd() / "configs"
        if not directory.exists():
            return 0, [Autocomplete.Option("", f"No configs/ directory was found.")]
        files = [f.name for f in Path(directory).iterdir() if f.is_file() and f.name.startswith(text) and f.name != text]
        return 0, list(Autocomplete.Option(file, "") for file in files)

    @console_command("developer", hint=lambda self: int(self.overlay._developer_mode))
    def set_developer_mode(self, enable: int):
        """If set, print stdout to the screen"""
        self.overlay._developer_mode = bool(enable)

    @console_command("showfps", hint=lambda self: int(self.overlay._show_fps))
    def set_fps_counter(self, enable: int):
        """Show or hide the FPS counter"""
        self.overlay._show_fps = bool(enable)

    @console_command("var_monitor", is_cheat_protected=True)
    def open_variable_monitor_window(self):
        self.overlay.children.append(VariableMonitorWindow(self.overlay, self.overlay, pg.Rect((200, 200), VariableMonitorWindow.SIZE)))

    @console_command(autocomplete_function=exec_cfg_autocomplete, is_cheat_protected=True)
    def exec_cfg(self, config: str) -> None:
        """Executes any file containing python code in the configs/ directory"""
        if not config.endswith(".cfg"):
            config += ".cfg"
        filename = Path.cwd() / "configs" / config
        if not filename.exists():
            print(f"Config {config} does not exist.")
            return
        with open(filename, 'r') as file:
            code = file.read()
            try:
                exec(code, None, self.overlay.namespace.__dict__)
            except Exception as e:
                self.print_exception_to_log(e)

    @console_command(show_return_value=True)
    def get_cwd(self) -> str:
        """Gives the path of the current working directory"""
        return os.getcwd()

    @console_command("change_cwd", "chdir", show_return_value=False, is_cheat_protected=True)
    def change_cwd(self, path: str) -> None:
        """Changes the CWD, relative paths only."""
        os.chdir(os.path.join(os.getcwd(), path))

    @staticmethod
    def find_commands(instance: CommandCarrierType) -> dict[str: Callable[..., Any]]:
        commands: dict[str: Callable[..., Any]] = dict()
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if not getattr(method, "_is_console_command", False):
                continue
            aliases = getattr(method, "_aliases", False)
            if aliases is not False and len(aliases) > 0:
                for alias in aliases:
                    commands[alias] = method
            else:
                commands[name] = method
        return commands

    def get_all_commands(self) -> dict[str: Callable[..., Any]]:
        all_commands: dict[str: Callable[..., Any]] = dict()
        for command_carrier in self.overlay.namespace.__dict__.values():
            all_commands.update(self.find_commands(command_carrier))
        return all_commands

    def list_all_commands(self):
        all_commands = self.get_all_commands().keys()
        if not all_commands:
            self.log.print("No console commands found.", color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)
            return
        self.log.print("List of all available commands: (type help <command> for help)", mirror_to_stdout=True)
        column_gap = 2
        column_width = max(len(command_name) for command_name in all_commands) + column_gap
        column_count = self.input_box.max_chars // column_width
        command_iterator = iter(all_commands)
        while True:
            chunk = list(islice(command_iterator, column_count))
            if not chunk:
                break
            self.log.print("".join(f"{command_name:<{column_width}}" for command_name in chunk),
                           color=self.overlay.SECONDARY_TEXT_COLOR, mirror_to_stdout=True)

    def help_autocomplete(self, text: str) -> tuple[int, list["Autocomplete.Option"]]:
        return 0, list(Autocomplete.Option(command, str(func.__doc__ or "")) for command, func in self.get_all_commands().items() if command.startswith(text) and command != text)

    @console_command(autocomplete_function=help_autocomplete)
    def help(self, command_name: str = None) -> None:
        """¯\\_(ツ)_/¯"""
        if not command_name:
            self.list_all_commands()
        elif (command := self.get_all_commands().get(command_name)) is not None:
            if command.__doc__:
                self.log.print(command.__doc__.strip(), mirror_to_stdout=True)
            self.print_usage_string(command)
        else:
            self.log.print(
                f"The command {command_name} could not be found.",
                color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)
        return

    @console_command
    def clear(self) -> None:
        """Clears the dev console"""
        self.log.history.clear()
        self.log.history_index = 0
        self.log.render()

    def eval_exec_autocomplete(self, text: str) -> tuple[int, list["Autocomplete.Option"]]:
        def get_callable_args(callable_attr):
            if not callable(callable_attr):
                return None

            try:
                sig = inspect.signature(callable_attr)
                formatted_params = []

                for name, param in sig.parameters.items():
                    if param.default is inspect.Parameter.empty:
                        formatted_params.append(f"{name}")
                    else:
                        formatted_params.append(f"{name}={param.default!r}")

                return f"({', '.join(formatted_params)})"
            except (ValueError, TypeError):
                # Handle case where signature can't be retrieved
                return None

        names = text.split(".")

        current = self.overlay.namespace
        for i, name in enumerate(names):
            attr = getattr(current, name, None)
            if i < len(names) - 1:
                current = attr
            else:
                position = sum(len(name) for name in names[0:i]) + i
                if hasattr(current, name):
                    position = sum(len(name) for name in names) + i
                    if inspect.ismethod(attr):
                        return position, [Autocomplete.Option(get_callable_args(attr), "")]

                options = []
                for current_name in dir(current):
                    obj = getattr(current, current_name)
                    if not current_name.startswith(name) or current_name == name or current_name.startswith("__"):
                        continue
                    if (str(obj).startswith("<") or str(obj).endswith(">")) and not callable(obj):
                        current_name += "."
                    if len(str(obj)) <= max(Autocomplete.MAX_UNSHORTENED_HINT_LENGTH, len(type(obj).__name__)):
                        hint: str = str(obj)
                        cursive = False
                    else:
                        hint: str = type(obj).__name__
                        cursive = True
                    options.append(Autocomplete.Option(current_name, hint, cursive))
                return position, options

    @console_command(is_cheat_protected=True, show_return_value=True, autocomplete_function=eval_exec_autocomplete)
    def eval(self, eval_string: str):
        """Evaluate an arbitrary string"""
        try:
            return eval(eval_string, None, self.overlay.namespace.__dict__)
        except Exception as e:
            self.print_exception_to_log(e)

    @console_command(is_cheat_protected=True, show_return_value=False, autocomplete_function=eval_exec_autocomplete)
    def exec(self, exec_string: str):
        """Execute an arbitrary string"""
        try:
            exec(exec_string, None, self.overlay.namespace.__dict__)
        except Exception as e:
            self.print_exception_to_log(e)

    @console_command("toggleconsole")
    def toggle_dev_console(self):
        """Toggles the developer console"""
        self.overlay.open = not self.overlay.open

    def handle_command(self, command: str, *, suppress_logging: bool = False, ignore_cheat_protection: bool = False):
        if not command:
            return
        if not suppress_logging:
            self.log.print(">>> " + command, color=self.overlay.PRIMARY_TEXT_COLOR, mirror_to_stdout=True)
        command_name, *args = command.split()
        func = self.get_all_commands().get(command_name)
        if func is None:
            self.log.print(f"No command {command_name} exists in the current game.", color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)
            return
        if getattr(func, "_is_cheat_protected", False) and not self.overlay.cheats_enabled and not ignore_cheat_protection:
            self.log.print(f"The command {command_name} is cheat protected.", color=self.overlay.HIGHLIGHT_COLOR, mirror_to_stdout=True)
            return
        try:
            cast_args = []
            for arg, (param_name, param) in zip(args, inspect.signature(func).parameters.items()):
                param_type = get_type_hints(func).get(param_name, "undef")
                if param_type == "undef":
                    cast_args.append(arg)
                elif type(param_type) is types.UnionType:
                    cast_arg = arg
                    for unioned_type in sorted(param_type.__args__, key=lambda t: t is str):
                        try:
                            cast_arg = unioned_type(arg)
                        except ValueError:
                            continue
                        break
                    cast_args.append(cast_arg)
                else:
                    try:
                        cast_args.append(param_type(arg))
                    except ValueError as e:
                        self.log.print(f"{e.__class__.__name__}: {str(e)}", color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)
            return_value = func(*cast_args)
            if getattr(func, "_show_return_value", False):
                self.log.print(str(return_value), mirror_to_stdout=True)
        except TypeError as e:
            self.log.print(f"{e.__class__.__name__}: {str(e)}", color=self.overlay.ERROR_COLOR, mirror_to_stdout=True)
            self.print_usage_string(func)
            return

    def print_usage_string(self, func: Callable[..., Any]):
        aliases = getattr(func, "_aliases", None)
        string = f"Usage: {"/".join(aliases)} " if aliases else f"Usage: {func.__name__} "
        for param_name, param in inspect.signature(func).parameters.items():
            param_type = get_type_hints(func).get(param_name, "undef")

            if param_type == "undef":
                param_type_name = "undef"
            elif hasattr(param_type, "__name__"):
                param_type_name = param_type.__name__
            else:
                param_type_name = str(param_type).replace(" ", "")

            param_default = param.default if param.default is not inspect.Parameter.empty else None
            if type(param_default) is str:
                param_default = "'" + param_default + "'"
            string += f"<{param_type_name} {param_name}{"=" + str(param_default) if param_default else ""}> "
        return_type = get_type_hints(func).get('return', "undef")
        return_type_name = return_type.__name__ if return_type != "undef" else "undef"
        string += f"-> {return_type_name}" if return_type_name != "NoneType" else ""
        self.log.print(string, mirror_to_stdout=True)

    def resize(self, new_height: int = 100):
        # This is janky af
        old_height = self.surface.get_height()
        new_height = min(self.overlay.surface.get_height(), max(self.input_box.surface.get_height() + 2 * self.overlay.border_offset, new_height))
        diff = new_height - old_height
        for child in self.children:
            child.rect.move_ip(0, diff)
        self.surface = pg.Surface((self.surface.get_width(), new_height))

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.toggle_dev_console()
        elif event.type == pg.KEYDOWN and (event.key == 1073741921 or event.key == pg.K_PAGEUP):
            self.resize(self.surface.get_height() - 50)
        elif event.type == pg.KEYDOWN and (event.key == 1073741915 or event.key == pg.K_PAGEDOWN):
            self.resize(self.surface.get_height() + 50)
        elif event.type == pg.MOUSEWHEEL:
            self.log.history_index -= event.y
            self.log.history_index = max(0, min(self.log.history_index, len(self.log.history)-1))
            self.log.render()
        elif self.input_box.handle_event(event):
            pass  # event got eaten by input box
        else:
            return False
        return True

    def render(self):
        self.surface.fill(self.overlay.PRIMARY_COLOR)

        visible_log_height = self.surface.get_height() - self.input_box.surface.get_height() - 3 * self.overlay.border_offset
        self.surface.blit(self.log.surface, (self.overlay.border_offset, self.overlay.border_offset),
                          (0, self.log.surface.get_height() - visible_log_height, self.log.surface.get_width(), visible_log_height))

        if visible_log_height > 0:
            self.draw_border_rect(self.surface, pg.Rect(self.overlay.border_offset, self.overlay.border_offset, self.log.surface.get_width(), visible_log_height), inset=True)
        self.render_border()


class Log(DeveloperOverlayElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: "DeveloperOverlayElement", rect: pg.Rect):
        super().__init__(overlay, parent, rect)
        self.surface.fill(overlay.SECONDARY_COLOR)

        self.history: list[tuple[str, tuple[int, int, int]]] = []
        self.history_index: int = 0

    def render(self):
        self.surface.fill(self.overlay.SECONDARY_COLOR)
        for line, color in reversed(self.history[self.history_index::-1]):
            self.print(line, color, mirror_to_stdout=False, append_to_history=False)

    def print(self, string: str, color: tuple[int, int, int] | None = None, *, mirror_to_stdout: bool = False, append_to_history: bool = True):
        if append_to_history:
            self.history.append((string, color))
            self.history_index = len(self.history)
        if mirror_to_stdout:
            print("DEV: " + string, file=sys.__stdout__)
        color = color if color is not None else self.overlay.SECONDARY_TEXT_COLOR
        font_surface = self.overlay.font.render(string, True, color, self.overlay.SECONDARY_COLOR)
        dy = -font_surface.get_height()
        self.surface.scroll(0, dy)
        self.surface.fill(self.overlay.SECONDARY_COLOR, (0, self.surface.get_height() + dy, self.surface.get_width(), -dy))
        self.surface.blit(font_surface, (0, self.surface.get_height() - font_surface.get_height()))
