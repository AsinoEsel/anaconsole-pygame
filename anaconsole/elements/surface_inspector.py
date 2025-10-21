import pygame as pg
from .base_element import BaseElement
from .window import Window
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay


class SurfaceInspector(BaseElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: BaseElement, rect: pg.Rect, inspect_surface: pg.Surface):
        super().__init__(overlay, parent, rect)
        self.inspect_surface: pg.Surface = inspect_surface

    def render_body(self):
        self.surface.blit(self.inspect_surface, (0, 0))


class SurfaceInspectorWindow(Window):
    SIZE: tuple[int, int] = (400, 250)

    def __init__(self, overlay: "DeveloperOverlay", parent: BaseElement, position: tuple[int, int],
                 inspect_surface: pg.Surface):
        super().__init__(overlay, parent, pg.Rect(position, self.SIZE), "Surface Inspector")
        self.children.append(
            SurfaceInspector(overlay, self, self.body_rect, inspect_surface)
        )
