import pygame
from anaconsole import DeveloperOverlay


class ExampleGame:
    def __init__(self):
        self.player: pygame.Rect = pygame.Rect(SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2, 50, 50)
        self.player_color = (255, 0, 0)
        self.player_velocity: pygame.Vector2 = pygame.Vector2(0, 0)

    def handle_event(self, event: pygame.event.Event):
        """Player movement logic"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.player_velocity.y -= 30
            elif event.key == pygame.K_DOWN:
                self.player_velocity.y += 30
            elif event.key == pygame.K_LEFT:
                self.player_velocity.x -= 30
            elif event.key == pygame.K_RIGHT:
                self.player_velocity.x += 30
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                self.player_velocity.y += 30
            elif event.key == pygame.K_DOWN:
                self.player_velocity.y -= 30
            elif event.key == pygame.K_LEFT:
                self.player_velocity.x += 30
            elif event.key == pygame.K_RIGHT:
                self.player_velocity.x -= 30

    def update(self):
        self.player.center += self.player_velocity

    def render(self):
        screen.fill((0, 0, 0, 0))
        pygame.draw.rect(screen, self.player_color, self.player)


if __name__ == "__main__":
    pygame.init()
    SCREEN_SIZE = (1280, 720)
    FRAMERATE = 60
    screen = pygame.display.set_mode(SCREEN_SIZE)

    example_game = ExampleGame()
    anaconsole = DeveloperOverlay(screen, {"game": example_game},
                                  enable_cheats=True,
                                  target_framerate=FRAMERATE)
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if anaconsole._trickle_down_event(event):
                continue
            example_game.handle_event(event)
        example_game.update()
        example_game.render()
        anaconsole.render()

        pygame.display.flip()
        pygame.event.pump()
        clock.tick(FRAMERATE)
