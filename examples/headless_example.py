from anaconsole import DeveloperOverlay
import pygame


if __name__ == '__main__':
    pygame.init()
    dev_overlay = DeveloperOverlay(pygame.Surface((1280, 720)), enable_cheats=True)
    while True:
        string = input(">>> ")
        dev_overlay.dev_console.handle_command(string, suppress_logging=True)
