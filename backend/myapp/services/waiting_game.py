import random


def run_waiting_game():
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((720, 420))
    pygame.display.set_caption("Download Waiting Game")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 34)
    player = pygame.Rect(70, 330, 28, 28)
    obstacles = []
    velocity = 0.0
    score = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type in {pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN} and player.bottom >= 380:
                velocity = -12

        velocity += 0.7
        player.y += int(velocity)
        if player.bottom >= 380:
            player.bottom = 380
            velocity = 0

        if random.random() < 0.018:
            obstacles.append(pygame.Rect(720, random.randint(330, 355), 24, random.randint(25, 50)))
        for obstacle in list(obstacles):
            obstacle.x -= 7
            if obstacle.right < 0:
                obstacles.remove(obstacle)
                score += 1
            elif player.colliderect(obstacle):
                score = 0
                obstacles.clear()

        screen.fill((247, 249, 252))
        pygame.draw.line(screen, (40, 48, 61), (0, 380), (720, 380), 2)
        pygame.draw.rect(screen, (0, 174, 236), player)
        for obstacle in obstacles:
            pygame.draw.rect(screen, (247, 76, 127), obstacle)
        screen.blit(font.render(f"Score {score}", True, (40, 48, 61)), (24, 24))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
