import pygame as pg
from typing import Type, Union, TYPE_CHECKING, Optional, Callable
from .dev_overlay_element import DeveloperOverlayElement
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay


class Slider(DeveloperOverlayElement):
    COLOR: tuple[int, int, int] = (31, 31, 31)
    GROOVE_WIDTH: int = 6
    SLIDER_SIZE: tuple[int, int] = (12, 24)
    TRANSPARENCY: tuple[int, int, int] = (0, 0, 0)

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect,
                 domain: Type[Union[int, float]],
                 value_range: tuple[int | float, int | float],
                 getter: Callable[[], int | float],
                 setter: Callable[[int | float], None], *,
                 vertical: bool = False):
        super().__init__(overlay, parent, rect, colorkey=self.TRANSPARENCY)
        self.domain = domain
        self.value_range: tuple[int | float, int | float] = value_range
        self.setter: Callable[[int | float], None] = setter
        self.getter: Callable[[], int | float] = getter
        self.vertical: bool = vertical
        self.groove_rect: pg.Rect = (
            pg.Rect(self.SLIDER_SIZE[0] // 2,
                    self.rect.h // 2 - self.GROOVE_WIDTH // 2,
                    self.rect.width - 2 * self.SLIDER_SIZE[0] // 2,
                    self.GROOVE_WIDTH)
            if not vertical else
            pg.Rect(self.rect.w // 2 - self.GROOVE_WIDTH // 2,
                    self.SLIDER_SIZE[0] // 2,
                    self.GROOVE_WIDTH,
                    self.rect.height - 2 * self.SLIDER_SIZE[0] // 2)
        )
        self.handle_rect: pg.Rect = (
            pg.Rect(self.groove_rect.left - self.SLIDER_SIZE[0]//2,
                    self.groove_rect.centery - self.SLIDER_SIZE[1]//2,
                    self.SLIDER_SIZE[0],
                    self.SLIDER_SIZE[1])
            if not vertical else
            pg.Rect(self.groove_rect.centerx - self.SLIDER_SIZE[1]//2,
                    self.groove_rect.top + self.SLIDER_SIZE[0]//2,
                    self.SLIDER_SIZE[1],
                    self.SLIDER_SIZE[0])
        )

    @staticmethod
    def maprange(value: int | float, start_range: tuple[int | float, int | float],
                 end_range: tuple[int | float, int | float]) -> float:
        w = (value - start_range[0]) / (start_range[1] - start_range[0])
        y = end_range[0] + w * (end_range[1] - end_range[0])
        return y

    def set_handle_position(self, value: int | float):
        handle_position_relative: float = abs((value - self.value_range[0]) / (self.value_range[1] - self.value_range[0]))
        if not self.vertical:
            self.handle_rect.left = handle_position_relative * self.groove_rect.w
        else:
            self.handle_rect.top = handle_position_relative * self.groove_rect.h

    def set_value(self, mouse_x: int):
        if not self.vertical:
            mapped_val = self.maprange(mouse_x, (self.groove_rect.left, self.groove_rect.right), self.value_range)
        else:
            mapped_val = self.maprange(mouse_x, (self.groove_rect.top, self.groove_rect.bottom), self.value_range)

        minimum, maximum = min(self.value_range), max(self.value_range)
        val = self.domain(min(maximum, max(minimum, mapped_val)))
        self.setter(val)

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION and pg.mouse.get_pressed()[0] and self.is_selected():
            self.set_value(event.pos[0] if not self.vertical else event.pos[1])
            return True
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.set_value(event.pos[0] if not self.vertical else event.pos[1])
            return True
        return False

    def render(self):
        self.surface.fill(self.TRANSPARENCY)
        self.set_handle_position(self.getter())
        pg.draw.rect(self.surface, self.COLOR, self.groove_rect)
        self.draw_border_rect(self.surface, self.groove_rect, inset=True)
        pg.draw.rect(self.surface, self.overlay.PRIMARY_COLOR, self.handle_rect)
        self.draw_border_rect(self.surface, self.handle_rect, inset=False)
