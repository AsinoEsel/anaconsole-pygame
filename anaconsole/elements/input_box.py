import pygame as pg
import pyperclip
from .base_element import BaseElement
from typing import Callable, TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay
    from .autocomplete import Autocomplete


class InputBox(BaseElement):
    INSET: bool = True
    STOP_CHARS: tuple[str] = (' ', '.', ',')
    PAIRED_DELIMITERS: dict[str:str] = {
        '"': '"',
        "'": "'",
        "(": ")",
        "[": "]",
        "{": "}",
    }

    def __init__(self, overlay: "DeveloperOverlay", parent: "BaseElement", rect: pg.Rect,
                 getter: Callable[[], str] | None = None,
                 setter: Callable[[str], None] = lambda x: None, *,
                 clear_on_send: bool = False,
                 select_all_on_click: bool = True,
                 lose_focus_on_send: bool = True,
                 validator: Callable[[str], bool] = lambda x: True,
                 autocomplete_function: Callable[[str], tuple[int, list["Autocomplete.Option"]]] | None = None,
                 alignment: Literal["left", "center", "right"] = "left",
                 ) -> None:
        super().__init__(overlay, parent, rect)
        self.getter: Callable[[], str] = getter if getter else lambda: self.text
        self.setter: Callable[[str], None] = setter
        self.clear_on_send: bool = clear_on_send
        self.select_all_on_click: bool = select_all_on_click
        self.lose_focus_on_send: bool = lose_focus_on_send
        self.validator: Callable[[str], bool] = validator
        self.autocomplete_function: Callable[[str], tuple[int, list["Autocomplete.Option"]]] | None = autocomplete_function
        self.alignment: Literal["left", "center", "right"] = alignment
        self.in_edit_mode: bool = False  # TODO: join feature with element selection
        self.in_history: bool = False  # TODO: find better solution that's less maintenance heavy
        self.text = getter() if getter else ""
        self.max_chars = self.surface.get_width()//self.overlay.char_width - 1
        self.caret_position = 0
        self.selection_range = None
        self.history: list[str] = []
        self.history_index = 0

    def update_autocomplete(self, text: str):
        # TODO: move into Autocomplete class instead? (Pass self)
        if not self.autocomplete_function:
            return
        self.overlay.autocomplete.selection_index = 0
        abs_rect = self.get_absolute_rect()
        self.overlay.autocomplete.rect.topleft = (abs_rect.left, abs_rect.bottom)
        self.overlay.autocomplete.input_box = self
        self.overlay.autocomplete.position, self.overlay.autocomplete.options = self.autocomplete_function(text)
        self.overlay.autocomplete.show = True if self.overlay.autocomplete.options else False

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and 0 < event.pos[0] < self.rect.w and 0 < event.pos[1] < self.rect.h:
            self.in_edit_mode = True
            if self.select_all_on_click:
                self.select_all()
        elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE and self.in_edit_mode:
            self.escape()
        elif event.type == pg.TEXTINPUT and self.in_edit_mode and (len(self.text) < self.max_chars or self.selection_range):
            if event.text in self.PAIRED_DELIMITERS.keys() and self.selection_range:
                self.text = (self.text[:min(self.selection_range)]
                             + event.text
                             + self.text[min(self.selection_range):max(self.selection_range)]
                             + self.PAIRED_DELIMITERS[event.text]
                             + self.text[max(self.selection_range):]
                             )
                self.selection_range = (self.selection_range[0] + 1, self.selection_range[1] + 1)
                return True
            self.in_history = False
            if self.selection_range:
                self.erase_selection_range()
            self.text = self.text[0:self.caret_position] + event.text + self.text[self.caret_position:]
            self.caret_position += 1
            self.update_autocomplete(self.text)
        elif event.type == pg.KEYDOWN and self.in_edit_mode:
            if event.key == pg.K_RETURN:
                self.in_history = False
                self.enter()
            elif event.key == pg.K_BACKSPACE:
                self.in_history = False
                if self.selection_range:
                    self.erase_selection_range()
                else:
                    self.move_caret(-1, holding_ctrl=event.mod & pg.KMOD_CTRL, delete=True)
                self.update_autocomplete(self.text)
            elif event.key == pg.K_DELETE:
                self.in_history = False
                if self.selection_range:
                    self.erase_selection_range()
                else:
                    self.move_caret(1, holding_ctrl=event.mod & pg.KMOD_CTRL, delete=True)
                self.update_autocomplete(self.text)
            elif event.key == pg.K_LEFT:
                self.in_history = False
                self.move_caret(-1, event.mod & pg.KMOD_SHIFT, event.mod & pg.KMOD_CTRL)
            elif event.key == pg.K_RIGHT:
                self.in_history = False
                self.move_caret(1, event.mod & pg.KMOD_SHIFT, event.mod & pg.KMOD_CTRL)
            elif event.key == pg.K_UP and (not self.text or self.in_history):
                if not self.in_history:
                    self.history_index = 0
                self.in_history = True
                if self.history_index > -len(self.history):
                    self.history_index -= 1
                    self.text = self.history[self.history_index]
                self.caret_position = len(self.text)
            elif event.key == pg.K_DOWN and (not self.text or self.in_history):
                if not self.in_history:
                    self.history_index = 0
                self.in_history = True
                if self.history_index < 0:
                    self.history_index += 1
                    self.text = self.history[self.history_index] if self.history_index != 0 else ""
                self.caret_position = len(self.text)
            elif event.key == pg.K_a and event.mod & pg.KMOD_CTRL:
                self.select_all()
            elif event.key == pg.K_c and event.mod & pg.KMOD_CTRL:
                if self.selection_range and self.selection_range[0] != self.selection_range[1]:
                    pyperclip.copy(self.text[min(self.selection_range):max(self.selection_range)])
            elif event.key == pg.K_x and event.mod & pg.KMOD_CTRL:
                self.in_history = False
                if self.selection_range and self.selection_range[0] != self.selection_range[1]:
                    pyperclip.copy(self.text[min(self.selection_range):max(self.selection_range)])
                    self.erase_selection_range()
            elif event.key == pg.K_v and event.mod & pg.KMOD_CTRL:
                self.in_history = False
                if clipboard := pyperclip.paste():
                    if self.selection_range:
                        self.erase_selection_range()
                    self.text = self.text[:self.caret_position] + clipboard + self.text[self.caret_position:]
                    self.move_caret(len(clipboard))
            return True  # Always eat KEYDOWN events!
        elif event.type == pg.KEYUP:
            return True  # Always eat KEYUP events! Workaround to prevent accidental button presses
        else:
            return False
        return True

    def select_all(self):
        if self.text:
            self.selection_range = [0, len(self.text)]

    def enter(self):
        if not self.validator(self.text):
            self.escape()
            return
        if self.lose_focus_on_send:
            self.in_edit_mode = False
        self.setter(self.text)
        if self.text:
            if self.text in self.history:
                self.history.remove(self.text)
            self.history.append(self.text)
        if self.clear_on_send:
            self.text = ''
            self.caret_position = 0
        self.update_autocomplete(self.text)
        self.selection_range = None
        self.history_index = 0

    def escape(self):
        self.in_edit_mode = False
        self.selection_range = None
        self.text = self.getter()

    def move_caret(self, amount: int, holding_shift: bool = False, holding_ctrl: bool = False, delete=False):
        original_position = self.caret_position
        if holding_ctrl:
            if amount > 0:
                indices = []
                for char in self.STOP_CHARS:
                    indices.append(self.text.find(char, self.caret_position))
                index = max(indices) if max(indices) != -1 else len(self.text)
            elif amount < 0:
                indices = []
                for char in self.STOP_CHARS:
                    indices.append(self.text.rfind(char, 0, max(0, self.caret_position - 1)))
                index = max(indices)
            else:
                return
            amount = index - self.caret_position + 1

        if not holding_shift and self.selection_range:
            if amount > 0:
                self.caret_position = max(self.selection_range)
            elif amount < 0:
                self.caret_position = min(self.selection_range)
        else:
            self.caret_position += amount
            self.caret_position = min(max(0, self.caret_position), len(self.text))

        if delete:
            self.text = self.text[:min(self.caret_position, original_position)] + self.text[max(self.caret_position,
                                                                                                original_position):]
            self.caret_position = min(self.caret_position, original_position)
        if not holding_shift:
            self.selection_range = None
        elif self.selection_range:
            self.selection_range[1] = self.caret_position
        else:
            self.selection_range = [original_position, self.caret_position]

    def erase_selection_range(self):
        self.text = self.text[0:min(self.selection_range)] + self.text[max(self.selection_range):]
        self.caret_position = min(self.selection_range)
        self.selection_range = None

    def render_text(self):
        text = self.text if self.in_edit_mode else self.getter()
        if not self.validator(text):
            color = self.overlay.ERROR_COLOR
        elif self.in_edit_mode:
            color = self.overlay.PRIMARY_TEXT_COLOR
        else:
            color = self.overlay.SECONDARY_TEXT_COLOR
        text_surface = self.overlay.font.render(text, True, color, None)
        self.surface.blit(text_surface, (self.get_letter_x(0), (self.rect.h - text_surface.get_height()) // 2))

    def get_letter_x(self, letter_position: int) -> int:
        if self.alignment == "left":
            return int(self.overlay.char_width * (letter_position + 1 / 3))
        elif self.alignment == "center":
            return self.rect.width//2 + self.overlay.char_width * (letter_position - len(self.text) / 2)
        elif self.alignment == "right":
            reverse_position: int = len(self.text) - letter_position
            return self.rect.width - int(self.overlay.char_width * (reverse_position + 1 / 3))
        raise ValueError

    def render_caret(self):
        x = self.get_letter_x(self.caret_position)
        pg.draw.line(self.surface, self.overlay.PRIMARY_TEXT_COLOR, (x, self.overlay.char_height // 6),
                     (x, self.rect.height - self.overlay.char_height // 6), 2)

    def render_selection(self):
        x = self.get_letter_x(min(self.selection_range))
        y = self.overlay.char_height // 8
        w = self.overlay.char_width * (max(self.selection_range) - min(self.selection_range))
        h = self.rect.height - 2 * self.overlay.char_height // 8
        pg.draw.rect(self.surface, self.overlay.HIGHLIGHT_COLOR, (x, y, w, h))

    def render_body(self):
        fill_color = self.overlay.PRIMARY_COLOR if not self.in_edit_mode else self.overlay.SECONDARY_COLOR
        self.surface.fill(fill_color)
        if self.selection_range:
            self.render_selection()
        self.render_text()
        if self.in_edit_mode and not self.selection_range:
            self.render_caret()
