import pygame as pg
from .base_element import BaseElement
from typing import Callable, TYPE_CHECKING, Optional
from anaconsole import MOUSEMOTION_2
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay


class Button(BaseElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["BaseElement"], rect: pg.Rect, callback: Callable[[], None], *,
                 image: pg.Surface | None = None,
                 toggle: bool = False,
                 locked: bool = False,
                 ):
        super().__init__(overlay, parent, rect)
        self.callback: Callable[[], None] = callback
        self.image: pg.Surface | None = image
        self.toggle: bool = toggle
        if toggle:
            self.state: bool = False
        self.highlighted: bool = False
        self.pressed: bool = False
        self.locked: bool = locked

    def render_body(self):
        self.surface.fill(self.overlay.PRIMARY_COLOR)
        if self.image:
            tinted_image = self.image.copy()
            if self.toggle and self.state:
                tinted_image.fill(self.overlay.HIGHLIGHT_COLOR, special_flags=pg.BLEND_RGB_MULT)
            if self.pressed:
                tinted_image.fill(self.overlay.SECONDARY_TEXT_COLOR, special_flags=pg.BLEND_RGB_MULT)
            dest = ((self.rect.w - self.image.get_width()) // 2, (self.rect.h - self.image.get_height()) // 2)
            self.surface.blit(tinted_image, dest if not self.pressed else (dest[0]+1, dest[1]+1))

    def render(self):
        self.render_body()
        self.render_border(inset=self.pressed)

    def trigger(self):
        self.pressed = False
        if self.toggle:
            self.state = not self.state
        self.callback()

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION:
            if self.is_selected() and pg.mouse.get_pressed()[0] and 0 < event.pos[0] < self.rect.w and 0 < event.pos[1] < self.rect.h and not self.locked:
                self.pressed = True
            self.highlighted = True
            return True
        elif event.type == MOUSEMOTION_2:
            if not 0 < event.pos[0] + event.rel[0] < self.rect.w or not 0 < event.pos[1] + event.rel[1] < self.rect.h:
                self.pressed = False
                self.highlighted = False
                self.render()
                return True
        elif event.type == pg.MOUSEBUTTONDOWN and not self.locked:
            self.pressed = True
        elif event.type == pg.MOUSEBUTTONUP and self.is_selected() and 0 < event.pos[0] < self.rect.w and 0 < event.pos[1] < self.rect.h and not self.locked:
            self.trigger()
            return True
        elif event.type == pg.KEYDOWN and (event.key == pg.K_RETURN or event.key == pg.K_SPACE) and not self.locked:
            self.pressed = True
            return True
        elif event.type == pg.KEYUP and (event.key == pg.K_RETURN or event.key == pg.K_SPACE) and not self.locked:
            self.trigger()
            return True
        return False
