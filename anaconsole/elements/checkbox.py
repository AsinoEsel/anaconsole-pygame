import pygame as pg
from anaconsole.assets import load_file_stream
from .base_element import BaseElement
from typing import Callable, TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay


class Checkbox(BaseElement):
    INSET: bool = True
    SIZE = 18
    CHECK_IMAGE: pg.Surface = pg.image.load(load_file_stream("check.png"))

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["BaseElement"],
                 position: tuple[int, int],
                 callback: Callable[[bool], None],
                 getter: Callable[[], bool] | None = None
                 ):
        super().__init__(overlay, parent, pg.Rect(position, (self.SIZE, self.SIZE)))
        self.getter: Callable[[], bool] = getter
        self.setter: Callable[[bool], None] = callback

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN:
            self.setter(not self.getter())
            return True
        return False

    def render_body(self):
        self.surface.fill(self.overlay.SECONDARY_COLOR)
        if self.getter():
            self.surface.blit(self.CHECK_IMAGE, (0, 0))
