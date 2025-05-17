import pygame as pg
from .base_element import BaseElement
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay
    from .input_box import InputBox


class Autocomplete(BaseElement):
    MAX_HINT_LENGTH = 32
    MAX_UNSHORTENED_HINT_LENGTH = 16

    @dataclass(frozen=True)
    class Option:
        name: str
        type_hint: str
        italics: bool = True

    def __init__(self, overlay: "DeveloperOverlay", position: tuple[int, int]):
        super().__init__(overlay, overlay, pg.Rect(position, (1, 1)))
        self.input_box: Optional["InputBox"] = None
        self.show: bool = False
        self.options: list[Autocomplete.Option] = []
        self.position: int = 0  # the position at which the autocomplete is inserted
        self.selection_index: int = 0

    def handle_event(self, event: pg.event.Event) -> bool:
        if self.show and event.type == pg.KEYDOWN and event.key == pg.K_DOWN:
            self.selection_index = (self.selection_index + 1) % len(self.options)
            self.draw()
        elif self.show and event.type == pg.KEYDOWN and event.key == pg.K_UP:
            self.selection_index = (self.selection_index - 1) % len(self.options)
            self.draw()
        elif self.show and event.type == pg.KEYDOWN and event.key == pg.K_TAB:
            self.input_box.text = self.input_box.text[0:self.position] + self.options[self.selection_index].name
            self.input_box.caret_position = len(self.input_box.text)
            self.input_box.update_autocomplete(self.input_box.text)  # TODO: why do we need this?
        else:
            return False
        return True

    def draw(self):
        surface_border_width = 2
        hint_gap = 1 if any(option.type_hint for option in self.options) else 0
        surface_width = max(len(option.name.rstrip()) + min(self.MAX_HINT_LENGTH, len(option.type_hint)) + hint_gap for option in self.options) * self.overlay.char_width + 2 * surface_border_width
        surface_height = len(self.options) * self.overlay.char_height + surface_border_width

        self.surface = pg.Surface((surface_width, surface_height))
        self.surface.fill(self.overlay.PRIMARY_COLOR)
        for i, option in enumerate(self.options):
            if i == self.selection_index:
                pg.draw.rect(self.surface, self.overlay.HIGHLIGHT_COLOR, (0, i * self.overlay.char_height, surface_width, self.overlay.char_height))
                text_color = self.overlay.PRIMARY_TEXT_COLOR
                hint_color = self.overlay.SECONDARY_TEXT_COLOR
            else:
                text_color = self.overlay.SECONDARY_TEXT_COLOR
                hint_color = self.overlay.BORDER_COLOR_LIGHT
            y = i * self.overlay.char_height + surface_border_width
            self.surface.blit(self.overlay.font.render(option.name, False, text_color, None), (surface_border_width, y))
            type_hint = option.type_hint if len(option.type_hint) <= self.MAX_HINT_LENGTH else option.type_hint[0:self.MAX_HINT_LENGTH-3]+"..."
            if option.italics:
                self.overlay.font.set_italic(True)
            self.surface.blit(self.overlay.font.render(type_hint, False, hint_color, None), (surface_width - len(type_hint) * self.overlay.char_width, y))
            self.overlay.font.set_italic(False)
        self.draw_border_rect(self.surface, pg.Rect(0, 0, self.surface.get_width(), self.surface.get_height()))  # TODO: cannot use self.render_border() here
