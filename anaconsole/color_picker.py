import pygame as pg
import numpy as np
import colorsys
import math
from .assets import load_file_stream
from .dev_overlay_element import DeveloperOverlayElement
from .slider import Slider
from .button import Button
from .window import Window
from .input_box import InputBox
from typing import Optional, TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay


def generate_color_wheel(size: int) -> pg.Surface:
    radius = size // 2
    surface = pg.Surface((size, size), pg.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    for x in range(size):
        for y in range(size):
            dx = x - radius
            dy = y - radius
            distance = np.sqrt(dx ** 2 + dy ** 2) / radius
            if distance > 1:
                continue
            else:
                hue = (np.arctan2(-dy, dx) + np.pi) / (2 * np.pi)  # 0 to 1
                saturation = distance  # 0 to 1
                rgb = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                rgb = tuple(int(c * 255) for c in rgb)
                surface.set_at((x, y), rgb)
    return surface


class ColorPicker(DeveloperOverlayElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect,
                 getter: Callable[[], tuple[int, int, int]] = lambda: (0, 0, 0),
                 setter: Callable[[tuple[int, int, int]], None] = lambda color: None,
                 ):
        super().__init__(overlay, parent, rect)
        self.getter: Callable[[], tuple[int, int, int]] = getter
        self.setter: Callable[[tuple[int, int, int]], None] = setter
        self.color_wheel = ColorWheel(overlay, self, (overlay.border_offset, (self.rect.h-ColorWheel.SIZE)//2), getter, self.setter_intercept)
        self.children.append(self.color_wheel)

        value_slider = Slider(overlay, self, pg.Rect(2 * overlay.border_offset + self.color_wheel.SIZE,
                                                     self.color_wheel.rect.top,
                                                     Slider.SLIDER_SIZE[1],
                                                     self.color_wheel.WHEEL_SIZE),
                              float, (1.0, 0.0),
                              self.value_getter(),
                              self.value_setter,
                              vertical=True)
        self.children.append(value_slider)

        slider_dist = 30
        sliders_x = value_slider.rect.right + overlay.border_offset
        sliders_y = value_slider.rect.top + slider_dist
        rgb_slider_width = self.rect.w - 4 * overlay.border_offset - self.color_wheel.SIZE - value_slider.rect.w
        rgb_sliders = [Slider(overlay, self, pg.Rect(sliders_x,
                                                     sliders_y + ch*slider_dist,
                                                     rgb_slider_width,
                                                     Slider.SLIDER_SIZE[1]),
                              int, (0, 255), self.rgb_getter(ch), self.rgb_setter(ch)) for ch in range(3)]
        self.children.extend(rgb_sliders)

        self.hex_input_box = InputBox(overlay, self, pg.Rect(sliders_x, rgb_sliders[-1].rect.bottom, overlay.char_width * 8, int(overlay.char_height * 1.5)),
                                      getter=self.hex_getter,
                                      setter=self.hex_setter,
                                      validator=self.hex_validator)
        self.children.append(self.hex_input_box)

    @staticmethod
    def hex_validator(user_input: str) -> bool:
        if user_input.startswith("#"):
            user_input = user_input[1:]
        valid_chars = set('0123456789abcdefABCDEF')
        if len(user_input) != 6 or not all(char in valid_chars for char in user_input):
            return False
        return True

    def setter_intercept(self, color: tuple[int, int, int]) -> None:
        """Intercepts the setter to update the elements of the color picker"""
        self.setter(color)
        self.hex_input_box.text = self.rgb_to_hex(color) # TODO: without this line, the input box always lags 1 color change behind. Why?
        self.color_wheel.draw_color_wheel()
        *self.color_wheel.caret_position, _ = self.color_wheel.rgb_to_wheel_coordinates(color)

    @staticmethod
    def hex_to_rgb(hex_code: str) -> tuple[int, int, int] | None:
        hex_color = hex_code.lstrip('#')
        # valid_chars = set('0123456789abcdefABCDEF')
        # if len(hex_color) != 6 or not all(char in valid_chars for char in hex_color):
        #     return None
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return r, g, b

    @staticmethod
    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    def hex_getter(self) -> str:
        return self.rgb_to_hex(self.getter())

    def hex_setter(self, hex_code: str) -> None:
        rgb: tuple[int, int, int] | None = self.hex_to_rgb(hex_code)
        if rgb:
            self.setter_intercept(rgb)

    def value_getter(self) -> Callable[[], float]:
        return lambda: colorsys.rgb_to_hsv(*[x / 255.0 for x in self.getter()])[2]

    def value_setter(self, val: float) -> None:
        self.color_wheel.draw_color_wheel(val)
        self.color_wheel.pick_color()

    def rgb_getter(self, channel: int) -> Callable[[], int]:
        return lambda: self.getter()[channel]

    def rgb_setter(self, channel: int) -> Callable[[int], None]:
        def setter(val: int) -> None:
            color: tuple[int, int, int] = self.getter()
            rgb: tuple[int, int, int] = tuple(x if i != channel else val for i, x in enumerate(color))
            self.setter_intercept(rgb)
        return setter


class ColorWheel(DeveloperOverlayElement):
    SIZE = 200
    WHEEL_SIZE = SIZE
    COLOR_PICKER_CARET: pg.Surface = pg.image.load(load_file_stream("color_picker_caret.png"))
    COLOR_WHEEL: pg.Surface = generate_color_wheel(SIZE)

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], pos: tuple[int, int],
                 getter: Callable[[], tuple[int, int, int]] = lambda: (0, 0, 0),
                 setter: Callable[[tuple[int, int, int]], None] = lambda color: None,
                 ):
        super().__init__(overlay, parent, pg.Rect(pos, (self.SIZE, self.SIZE)))
        self.getter: Callable[[], tuple[int, int, int]] = getter
        self.setter: Callable[[tuple[int, int, int]], None] = setter
        caret_x, caret_y, value = self.rgb_to_wheel_coordinates(getter())
        self.caret_position: tuple[int, int] = (caret_x, caret_y)
        self.color_wheel: pg.Surface = self.COLOR_WHEEL.copy()
        self.draw_color_wheel()

    def draw_color_wheel(self, value: float | None = None):
        self.color_wheel.blit(self.COLOR_WHEEL, (0, 0))
        value: float = colorsys.rgb_to_hsv(*[x/255.0 for x in self.getter()])[2] if value is None else value
        value_norm: int = int(255 * value)
        self.color_wheel.fill((value_norm, value_norm, value_norm), special_flags=pg.BLEND_RGB_MULT)

    def rgb_to_wheel_coordinates(self, rgb: tuple[int, int, int]) -> tuple[int, int, float]:
        # Normalize RGB
        r, g, b = [c / 255.0 for c in rgb]

        # Convert RGB to HSV
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        # Convert hue (0–1) to angle
        angle = h * 2 * math.pi

        # Convert polar (angle, s) to cartesian (x, y)
        radius = (self.WHEEL_SIZE // 2) * s
        cx = self.WHEEL_SIZE // 2
        cy = self.WHEEL_SIZE // 2
        x = int(cx - radius * math.cos(angle))
        y = int(cy + radius * math.sin(angle))  # y-axis inverted in screen coords

        return x, y, v

    def pick_color(self):
        r, g, b, a = self.color_wheel.get_at(self.caret_position)
        self.setter((r, g, b))

    def get_position_inside_wheel(self, position: tuple[int, int]) -> bool:
        return pg.Vector2(position).distance_squared_to(pg.Vector2(self.rect.w // 2, self.rect.h // 2)) < (self.SIZE // 2) ** 2

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and self.get_position_inside_wheel(event.pos):
            self.caret_position = event.pos
            self.pick_color()
            return True
        elif event.type == pg.MOUSEMOTION and pg.mouse.get_pressed()[0] and self.is_selected() and self.get_position_inside_wheel(event.pos):
            self.caret_position = event.pos
            self.pick_color()
            return True
        return False

    def render(self):
        self.surface.fill(self.overlay.PRIMARY_COLOR)
        self.surface.blit(self.color_wheel, (0, 0))
        pg.draw.circle(self.surface, self.overlay.BORDER_COLOR_DARK, (self.rect.w // 2, self.rect.h // 2), self.rect.w // 2, 1)
        pg.draw.circle(self.surface, self.overlay.BORDER_COLOR_LIGHT, (self.rect.w // 2, self.rect.h // 2), self.rect.w // 2, 1, draw_bottom_right=True)
        self.surface.blit(self.COLOR_PICKER_CARET, (self.caret_position[0] - 3, self.caret_position[1] - 3))


class ColorPickerWindow(Window):
    SIZE: tuple[int, int] = (400, 250)
    CONFIRM_BUTTON_SIZE: tuple[int, int] = (60, 20)

    def __init__(self, overlay: "DeveloperOverlay", parent: "DeveloperOverlayElement", position: tuple[int, int],
                 getter: Callable[[], tuple[int, int, int]] = lambda: (0, 0, 0),
                 setter: Callable[[tuple[int, int, int]], None] = lambda color: None,
                 ):
        super().__init__(overlay, parent, pg.Rect(position, self.SIZE), "Color Picker")
        self.children.append(ColorPicker(overlay, self, self.body_rect, getter, setter))
        self.children.append(Button(overlay, self, pg.Rect(self.rect.w - self.CONFIRM_BUTTON_SIZE[0] - overlay.border_offset,
                                                           self.rect.h - self.CONFIRM_BUTTON_SIZE[1] - overlay.border_offset,
                                                           self.CONFIRM_BUTTON_SIZE[0],
                                                           self.CONFIRM_BUTTON_SIZE[1]), self.close,
                                    image=overlay.font2.render("Confirm", False, overlay.PRIMARY_TEXT_COLOR, overlay.PRIMARY_COLOR)))


class ColorButton(Button):
    def __init__(self, overlay: "DeveloperOverlay", parent: "DeveloperOverlayElement", rect: pg.Rect,
                 getter: Callable[[], tuple[int, int, int]] = lambda: (0, 0, 0),
                 setter: Callable[[tuple[int, int, int]], None] = lambda color: None,
                 ):
        super().__init__(overlay, parent, rect, self.open_color_picker_window)
        self.color_getter = getter
        self.color_setter = setter

    def open_color_picker_window(self) -> None:
        color_picker_window = ColorPickerWindow(self.overlay, self.overlay, (300, 500),
                                                getter=self.color_getter,
                                                setter=self.color_setter
                                                )
        if self.get_parent_window() and self.get_parent_window().pinned:
            color_picker_window.pinned = True
            color_picker_window.children[1].state = True  # TODO: ugly workaround to fix pin button showing wrong color
        self.overlay.children.append(color_picker_window)

    def render_body(self):
        self.surface.fill(self.color_getter())
