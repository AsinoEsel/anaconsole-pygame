import pygame as pg
from typing import TYPE_CHECKING, Optional, Union
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay
    from .window import Window


class DeveloperOverlayElement:
    INSET: bool = False

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect, *, colorkey: tuple[int, int, int] | None = None):
        self.overlay: "DeveloperOverlay" = overlay
        self.parent: DeveloperOverlayElement | None = parent
        self.rect: pg.Rect = rect
        self.surface: pg.Surface = pg.Surface(rect.size)
        if colorkey:
            self.surface.set_colorkey(colorkey)
        self.children: list[DeveloperOverlayElement] = []
        self.selected_child: DeveloperOverlayElement | None = None

    def get_absolute_rect(self) -> pg.Rect:
        from .dev_overlay import DeveloperOverlay
        current = self
        current_x, current_y = 0, 0
        while not isinstance(current, DeveloperOverlay):
            current_x += current.rect.left
            current_y += current.rect.top
            current = current.parent
        return pg.Rect(current_x, current_y, self.rect.w, self.rect.h)

    def get_parent_window(self) -> Union["Window", None]:
        from .window import Window
        from .dev_overlay import DeveloperOverlay
        current = self
        while not isinstance(current, Window):
            if isinstance(current, DeveloperOverlay):
                return None
            current = current.parent
        return current

    def is_selected(self, *, must_be_last_in_linked_list: bool = True) -> bool:
        if self.selected_child is not None and must_be_last_in_linked_list:
            return False  # not the last selected object in the linked list
        current = self
        while current is not self.overlay:  # recursively walk up the parent hierarchy
            if current.parent.selected_child is not current:  # if link is broken, not selected
                return False
            else:
                current = current.parent
        return True  # we reached the top of the linked list, so we are the selected object

    def render_recursively(self, surface: pg.Surface):
        self.render()
        for child in self.children:
            child.render_recursively(self.surface)
        surface.blit(self.surface, self.rect)

    def render_body(self):
        self.surface.fill(self.overlay.PRIMARY_COLOR)

    def draw_border_rect(self, surface: pg.Surface, rect: pg.Rect, *, offset: int = 0, inset: bool = False):
        primary_color, secondary_color = (
            self.overlay.BORDER_COLOR_LIGHT, self.overlay.BORDER_COLOR_DARK
        ) if not inset else (
            self.overlay.BORDER_COLOR_DARK, self.overlay.BORDER_COLOR_LIGHT
        )
        pixel_offset = 1 if offset % 2 == 0 else 0
        left, top, width, height = (rect.left + offset,
                                    rect.top + offset,
                                    rect.w - offset - pixel_offset,
                                    rect.h - offset - pixel_offset)
        pg.draw.line(surface, primary_color, (left, top), (left, top + height), 1)
        pg.draw.line(surface, secondary_color, (left + width, top), (left + width, top + height), 1)
        pg.draw.line(surface, primary_color, (left, top), (left + width, top), 1)
        pg.draw.line(surface, secondary_color, (left, top + height), (left + width, top + height), 1)

    def render_border(self, inset: bool | None = None):
        inset: bool = inset if inset is not None else self.INSET
        # self.draw_border_rect(self.surface, self.rect, inset=inset)  # TODO: cannot use self.rect because of position offset

        left, top, width, height = 0, 0, self.rect.w - 1, self.rect.h - 1
        primary_color, secondary_color = (
            self.overlay.BORDER_COLOR_LIGHT, self.overlay.BORDER_COLOR_DARK
        ) if not inset else (
            self.overlay.BORDER_COLOR_DARK, self.overlay.BORDER_COLOR_LIGHT
        )
        pg.draw.line(self.surface, primary_color, (left, top), (left, top + height), 1)
        pg.draw.line(self.surface, secondary_color, (left + width, top), (left + width, top + height), 1)
        pg.draw.line(self.surface, primary_color, (left, top), (left + width, top), 1)
        pg.draw.line(self.surface, secondary_color, (left, top + height), (left + width, top + height), 1)

    def render(self):
        self.render_body()
        self.render_border()

    def select_next(self):
        if not self.selected_child:
            if self.children:
                self.selected_child = self.children[0]
            else:
                self.parent.select_next()
        else:
            index = self.children.index(self.selected_child)
            index += 1
            if index >= len(self.children):
                if self.parent:
                    self.parent.select_next()
                    return
                index = 0
            self.selected_child = self.children[index]
            self.selected_child.selected_child = None

    def get_selected_element(self) -> Optional["DeveloperOverlayElement"]:
        current = self
        while current.selected_child is not None:
            current = current.selected_child
        return current if current is not self else None

    def handle_event_recursively(self, event: pg.event.Event):
        if hasattr(event, "pos"):
            event.pos = (event.pos[0] - self.rect.left, event.pos[1] - self.rect.top)

        if self.handle_event(event):
            return True  # eaten by itself

        for child in self.children:
            if hasattr(event, "pos") and not child.rect.collidepoint(event.pos):
                continue
            if event.type == pg.MOUSEBUTTONDOWN:  # TODO: child selection
                self.selected_child = child
            if child.handle_event_recursively(event):
                return True  # eaten by child

        if event.type == pg.MOUSEBUTTONDOWN and not any(child.rect.collidepoint(event.pos) for child in self.children):
            self.selected_child = None

        if hasattr(event, "pos"):
            event.pos = (event.pos[0] + self.rect.left, event.pos[1] + self.rect.top)
        return False

    def handle_event(self, event: pg.event.Event) -> bool:
        return False
