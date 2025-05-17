import pygame as pg
MOUSEMOTION_2 = pg.event.custom_type()  # Custom event that mimics MOUSEMOTION
from .dev_overlay import DeveloperOverlay
from .elements.dev_console import console_command
from .elements.autocomplete import Autocomplete
