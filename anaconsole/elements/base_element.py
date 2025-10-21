import pygame as pg
from typing import TYPE_CHECKING, Optional, Union
if TYPE_CHECKING:
    from anaconsole.dev_overlay import DeveloperOverlay
    from anaconsole.elements.window import Window


class BaseElement:
    INSET: bool = False

    def __init__(self,
                 overlay: "DeveloperOverlay",
                 parent: Optional["BaseElement"],
                 rect: pg.Rect,
                 *,
                 colorkey: tuple[int, int, int] | None = None
                 ) -> None:
        self.overlay: "DeveloperOverlay" = overlay
        self.parent: BaseElement | None = parent
        self.rect: pg.Rect = rect
        self.surface: pg.Surface = pg.Surface(rect.size)
        if colorkey:
            self.surface.set_colorkey(colorkey)
        self.children: list[BaseElement] = []
        self.selected_child: BaseElement | None = None

    def get_absolute_rect(self) -> pg.Rect:
        from anaconsole.dev_overlay import DeveloperOverlay
        current = self
        current_x, current_y = 0, 0
        while current.parent is not None:
            current_x += current.rect.left
            current_y += current.rect.top
            current = current.parent
        return pg.Rect(current_x, current_y, self.rect.w, self.rect.h)

    def get_parent_window(self) -> Union["Window", None]:
        from anaconsole.dev_overlay import DeveloperOverlay
        from .window import Window
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
        if self.overlay.in_tab_mode and self.is_selected():
            pg.draw.rect(self.surface, (255, 255, 255), (0, 0, self.rect.w, self.rect.h), 1)
            return

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

    def resize(self, size: tuple[int, int]):
        colorkey: tuple[int, int, int, int] | None = self.surface.get_colorkey()
        self.surface = pg.Surface(size)
        if colorkey:
            self.surface.set_colorkey(colorkey)

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
            self.selected_child._trickle_down_deselect()
            self.selected_child = self.children[index]
            self.selected_child.selected_child = None

    def get_selected_element(self) -> Optional["BaseElement"]:
        current = self
        while current.selected_child is not None:
            current = current.selected_child
        return current if current is not self else None

    def deselect(self):
        pass

    def _trickle_down_deselect(self) -> None:
        self.deselect()
        if self.selected_child:
            self.selected_child.deselect()

    def highlight_selected_element(self):
        if self.selected_child:
            if not self.selected_child.selected_child:
                pg.draw.rect(self.surface, (255, 255, 255), self.selected_child.rect, 2)
            else:
                self.selected_child.highlight_selected_element()

    @staticmethod
    def is_mouse_event(event: pg.event.Event) -> bool:
        return hasattr(event, "pos")

    def _trickle_down_event(self, event: pg.event.Event) -> bool:
        # If the event is a mouse event, we correct the position tuple to be relative to our rect
        if self.is_mouse_event(event):
            event.pos = (event.pos[0] - self.rect.left, event.pos[1] - self.rect.top)

        # We first handle the event ourselves. If it gets processed, we stop the trickle here.
        if self.handle_event(event):
            return True

        # Child selection logic happens here. If LMB is pressed, we iterate over all children and perform collision
        # checks. If a child is found, we mark it as selected and deselect the previously selected child.
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            found_child: BaseElement | None = None
            for child in self.children:
                if child.rect.collidepoint(event.pos):
                    found_child = child
                    break
            if found_child is not self.selected_child:
                if self.selected_child is not None:
                    self.selected_child._trickle_down_deselect()
                self.selected_child = found_child

        # We finally trickle the event down to our selected child.
        if self.selected_child:
            return self.selected_child._trickle_down_event(event)
        return False

    def handle_event(self, event: pg.event.Event) -> bool:
        return False
