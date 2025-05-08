import pygame as pg
from .assets import load_file_stream
from .dev_overlay_element import DeveloperOverlayElement
from .button import Button
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay


class Window(DeveloperOverlayElement):
    CLOSE_BUTTON_IMAGE: pg.Surface = pg.image.load(load_file_stream("x.png"))
    PIN_BUTTON_IMAGE: pg.Surface = pg.image.load(load_file_stream("pin.png"))
    BUTTON_SIZE: int = 14

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect, title: str):
        super().__init__(overlay, parent, rect)
        self.title: str = title
        close_button: Button = Button(overlay, self,
                                      pg.Rect(self.rect.w - self.overlay.border_offset - self.BUTTON_SIZE,
                                              self.overlay.border_offset,
                                              self.BUTTON_SIZE, self.BUTTON_SIZE),
                                      self.close,
                                      image=self.CLOSE_BUTTON_IMAGE,
                                      )
        pin_button: Button = Button(overlay, self,
                                    pg.Rect(self.rect.w - 2 * self.BUTTON_SIZE - 2 * self.overlay.border_offset,
                                            self.overlay.border_offset,
                                            self.BUTTON_SIZE, self.BUTTON_SIZE),
                                    self.toggle_pinned,
                                    image=self.PIN_BUTTON_IMAGE,
                                    toggle=True
                                    )
        self.children.append(close_button)
        self.children.append(pin_button)
        self.body_rect = pg.Rect(self.overlay.border_offset,
                                 self.overlay.border_offset + self.overlay.char_height,
                                 self.rect.w - 2 * self.overlay.border_offset,
                                 self.rect.h - 2 * self.overlay.border_offset - self.overlay.char_height)
        self.pinned = False

    def toggle_pinned(self):
        self.pinned = not self.pinned

    def close(self):
        if self.is_selected(must_be_last_in_linked_list=False):
            self.parent.select_next()
        self.overlay.children.remove(self)
        del self

    def render(self):
        super().render()
        self.render_header()

    def render_header(self):
        title_surface = self.overlay.font.render(self.title, False, self.overlay.PRIMARY_TEXT_COLOR, self.overlay.PRIMARY_COLOR)
        self.surface.blit(title_surface, (self.overlay.border_offset, self.overlay.border_offset))

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION and pg.mouse.get_pressed()[0] and self.is_selected():
            self.rect.move_ip(event.rel)
            # self.rect.right = min(self.rect.right, self.parent.rect.right)  # TODO: clamp window position
            # ...
            return True
        return False
