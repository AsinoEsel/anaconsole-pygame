import pygame as pg
from .assets import load_file_stream
from .dev_overlay_element import DeveloperOverlayElement
from .checkbox import Checkbox
from .button import Button
from .slider import Slider
from .input_box import InputBox
from .window import Window
from .color_picker import ColorButton
from typing import Callable, TYPE_CHECKING, Optional, Any, get_type_hints, Type
from types import MethodType
if TYPE_CHECKING:
    from .dev_overlay import DeveloperOverlay


class Variable(DeveloperOverlayElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect,
                 var_name: str, var_type: type, var_getter: Callable[[], Any], var_setter: Callable[[Any], None], **kwargs):
        super().__init__(overlay, parent, rect)
        self.name: str = var_name
        self.type: type = var_type
        self.getter: Callable[[], Any] = var_getter
        self.setter: Callable[[Any], None] = var_setter

        if var_type in (int, float):
            value_range: tuple[int | float, int | float] = kwargs.get("value_range") if kwargs.get("value_range") else (0, 255) if var_type is int else (0.0, 1.0)
            self.children.append(Slider(overlay, self, pg.Rect(self.rect.centerx, 0, self.rect.w//2, self.rect.h), var_type, value_range, var_getter, var_setter))
        elif var_type == tuple[int, int, int] or (type(var_getter()) is tuple and len(var_getter()) == 3 and all(type(elem) is int for elem in var_getter())):
            height: int = self.rect.h - 2 * self.overlay.border_offset
            offset: int = (self.rect.h - height) // 2
            self.children.append(ColorButton(overlay, self, pg.Rect(self.rect.centerx, offset, self.rect.w//2-offset, height), var_getter, var_setter))
        elif var_type is bool:
            offset: int = (self.rect.h - Checkbox.SIZE) // 2
            self.children.append(Checkbox(overlay, self, (self.rect.right-Checkbox.SIZE-offset, offset), var_setter, var_getter))
        elif var_type is str:
            height: int = self.rect.h - 2 * self.overlay.border_offset
            offset: int = (self.rect.h - height) // 2
            self.children.append(InputBox(overlay, self, pg.Rect(self.rect.centerx, offset, self.rect.w//2-offset, height),
                                          getter=var_getter,
                                          setter=var_setter,
                                          alignment="center"))
        elif isinstance(var_setter, MethodType):
            height: int = self.rect.h - 2 * self.overlay.border_offset
            offset: int = (self.rect.h - height) // 2
            self.children.append(Button(overlay, self, pg.Rect(self.rect.centerx, offset, self.rect.w//2-offset, height),
                                        callback=var_setter,
                                        image=overlay.font2.render(f"Run {var_setter.__name__}", False, overlay.PRIMARY_TEXT_COLOR, overlay.PRIMARY_COLOR)))
        else:
            height: int = self.rect.h - 2 * self.overlay.border_offset
            offset: int = (self.rect.h - height) // 2
            self.children.append(InputBox(overlay, self, pg.Rect(self.rect.centerx, offset, self.rect.w // 2 - offset, height),
                                          getter=lambda: str(var_getter()),
                                          setter=self.misc_var_setter_getter(var_type, var_setter),
                                          alignment="center"))

    @staticmethod
    def misc_var_setter_getter(var_type: Type, var_setter: Callable[[Any], None]) -> Callable[[str], None]:
        def misc_var_setter(string: str) -> None:
            evaluated_string = eval(string)
            try:
                cast_obj: var_type = var_type(evaluated_string)
                var_setter(cast_obj)
            except (ValueError, TypeError):
                return
        return misc_var_setter

    def render(self):
        super().render()
        name_surf = self.overlay.font2.render(self.name, False, self.overlay.PRIMARY_TEXT_COLOR, self.overlay.PRIMARY_COLOR)
        val = self.getter()
        if isinstance(val, float):
            val = round(val, 2)
        val_surf = self.overlay.font2.render(str(val), False, self.overlay.SECONDARY_TEXT_COLOR, self.overlay.PRIMARY_COLOR)
        offset = self.rect.h//2 - name_surf.get_height() // 2
        self.surface.blit(name_surf, (2 * offset, offset))
        edit_element_width = self.children[0].rect.w if self.children else 0
        self.surface.blit(val_surf, (self.rect.w - edit_element_width - val_surf.get_width() - offset, offset))


class VariableMonitor(DeveloperOverlayElement):
    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect):
        super().__init__(overlay, parent, rect)
        self.variable_height: int = int(overlay.char_height * 1.75) // 2 * 2
        add_image: pg.Surface = pg.image.load(load_file_stream("add.png"))
        add_image.fill(overlay.HIGHLIGHT_COLOR + (255,), special_flags=pg.BLEND_RGB_MULT)
        text_surf: pg.Surface = overlay.font2.render("Add variable", False, overlay.HIGHLIGHT_COLOR, overlay.PRIMARY_COLOR)
        button_surf: pg.Surface = pg.Surface(((add_image.get_width()+overlay.border_offset+text_surf.get_width()), max(add_image.get_height(), text_surf.get_height())))
        button_surf.fill(overlay.PRIMARY_COLOR)
        button_surf.blit(add_image, (0, (button_surf.get_height()-add_image.get_height()) // 2))
        button_surf.blit(text_surf, (add_image.get_width()+overlay.border_offset, (button_surf.get_height()-text_surf.get_height()) // 2))
        self.new_var_button = Button(overlay, self, pg.Rect(0, 0, self.rect.w, self.variable_height),
                                     callback=self.new_var_button_callback,
                                     image=button_surf)
        self.children.append(self.new_var_button)

    def new_var_button_callback(self) -> None:
        if self.new_var_button.children:
            return
        var_name_input_box = InputBox(self.overlay, self.new_var_button,
                                      pg.Rect(0 + self.overlay.border_offset,
                                              0 + self.overlay.border_offset,
                                              self.new_var_button.rect.w - 2*self.overlay.border_offset,
                                              self.new_var_button.rect.h - 2*self.overlay.border_offset),
                                      autocomplete_function=self.overlay.dev_console.eval_exec_autocomplete,
                                      getter=None,
                                      validator=self.object_validator,
                                      setter=self.object_setter,
                                      )
        self.new_var_button.children.append(var_name_input_box)
        self.new_var_button.selected_child = var_name_input_box

    def object_validator(self, text: str) -> bool:
        if any(char in text for char in ("(", ")")) or not "." in text:
            return False
        try:
            eval(text, None, self.overlay.namespace.__dict__)
        except (SyntaxError, NameError, AttributeError):
            return False
        return True

    def object_setter(self, text: str) -> None:
        object_name, attr = text.rsplit(".", maxsplit=1)
        obj = eval(object_name, None, self.overlay.namespace.__dict__)
        self.register_variable(obj, attr, attr)
        self.new_var_button.children.clear()

    def register_variable(self, obj: object, attr: str, name: str = None, **kwargs: dict[str:Any]):
        rect = pg.Rect(0, (len(self.children) - 1) * self.variable_height, self.rect.w, self.variable_height)
        self.new_var_button.rect.top += self.variable_height
        var_name = name or attr
        var_type = get_type_hints(obj.__class__).get(attr) or type(getattr(obj, attr))
        if callable(getattr(obj, attr)):
            variable = Variable(self.overlay, self, rect, var_name, var_type, lambda: "", getattr(obj, attr), **kwargs)
        else:
            def getter(): return getattr(obj, attr)
            def setter(var): setattr(obj, attr, var)
            variable = Variable(self.overlay, self, rect, var_name, var_type, getter, setter, **kwargs)
        self.children.insert(-1, variable)


class VariableMonitorWindow(Window):
    SIZE: tuple[int, int] = (400, 450)

    def __init__(self, overlay: "DeveloperOverlay", parent: Optional["DeveloperOverlayElement"], rect: pg.Rect):
        super().__init__(overlay, parent, rect, title="Variable Monitor Window")
        self.children.append(VariableMonitor(overlay, self, self.body_rect))
