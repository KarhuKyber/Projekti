import pygame
from database import DatabaseManager, GameEngine, GameMode

pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 600
GRAY = (110, 110, 110)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hi-Lo Game")

# Fonts
small_font = pygame.font.Font(None, 32)
large_font = pygame.font.Font(None, 50)

# Buttons
high_button = large_font.render("HIGH", True, WHITE)
high_button_rect = high_button.get_rect(center=(280, 400))
low_button = large_font.render("LOW", True, WHITE)
low_button_rect = low_button.get_rect(center=(520, 400))

# Menu Buttons
pelaa = large_font.render("Pelaa", True, WHITE)
pelaa_rect = pelaa.get_rect(center=(200, 200))
omat_tilastot = large_font.render("Omat tilastot", True, WHITE)
omat_tilastot_rect = omat_tilastot.get_rect(center=(400, 200))
kirjaudu_sisaan = large_font.render("Kirjaudu sisään", True, WHITE)
kirjaudu_sisaan_rect = kirjaudu_sisaan.get_rect(center=(600, 200))
top_10 = large_font.render("Top 10", True, WHITE)
top_10_rect = top_10.get_rect(center=(800, 200))


def clear_screen():
    screen.fill(GRAY)
    pygame.display.update()


def show_main_menu():
    """Päävalikko"""
    while True:
        clear_screen()
        screen.blit(pelaa, pelaa_rect)
        screen.blit(omat_tilastot, omat_tilastot_rect)
        screen.blit(kirjaudu_sisaan, kirjaudu_sisaan_rect)
        screen.blit(top_10, top_10_rect)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if pelaa_rect.collidepoint(event.pos):
                    return "1"
                elif omat_tilastot_rect.collidepoint(event.pos):
                    return "2"
                elif top_10_rect.collidepoint(event.pos):
                    return "3"
                elif kirjaudu_sisaan_rect.collidepoint(event.pos):
                    return "4"


def login_or_register(db: DatabaseManager):
    """Kirjautuminen"""
    user_text = ""
    base_font = pygame.font.Font(None, 32)
    input_rect = pygame.Rect(300, 200, 200, 40)
    color = pygame.Color("lightskyblue3")

    while True:
        clear_screen()
        prompt = large_font.render("Anna käyttäjänimi:", True, WHITE)
        screen.blit(prompt, (200, 150))

        pygame.draw.rect(screen, color, input_rect)
        text_surface = base_font.render(user_text, True, WHITE)
        screen.blit(text_surface, (input_rect.x + 5, input_rect.y + 5))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if len(user_text) >= 3:
                        player_id = db.get_or_create_player(user_text)
                        if player_id:
                            return player_id, user_text
                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]
                else:
                    user_text += event.unicode


def play_game(db, player_id, username):
    """Pelin päälooppi"""
    game = GameEngine(db)
    game.start_new_game(player_id, username)

    while not game.state.game_over:
        display = game.get_current_display()

        clear_screen()
        screen.blit(large_font.render(f"Pelaaja: {display['player_username']}", True, WHITE), (50, 20))
        screen.blit(large_font.render(f"Pisteet: {display['score']}", True, WHITE), (50, 60))
        screen.blit(large_font.render(f"Elämät: {display['lives']}", True, WHITE), (50, 100))
        screen.blit(large_font.render(f"Ennätys: {display['high_score']}", True, WHITE), (50, 140))
        screen.blit(large_font.render(f"Kysymys: {display['question_type']}", True, WHITE), (50, 180))
        screen.blit(large_font.render(f"Nykyinen: {display['current_item']}", True, WHITE), (50, 220))
        screen.blit(large_font.render(f"Korkeus: {display['current_value']} ft", True, WHITE), (50, 260))
        screen.blit(large_font.render(f"Seuraava: {display['next_item']}", True, WHITE), (50, 300))
        screen.blit(high_button, high_button_rect)
        screen.blit(low_button, low_button_rect)
        pygame.display.update()

        choice = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if high_button_rect.collidepoint(event.pos):
                    choice = "h"
                elif low_button_rect.collidepoint(event.pos):
                    choice = "l"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    choice = "h"
                elif event.key == pygame.K_l:
                    choice = "l"
                elif event.key == pygame.K_q:
                    return

        if choice:
            is_higher = choice == "h"
            correct, message = game.make_guess(is_higher)
            if not correct:
                msg = large_font.render("Väärin!", True, RED)
                screen.blit(msg, (WIDTH // 2 - 100, HEIGHT // 2))
                pygame.display.update()
                pygame.time.delay(1500)

    # Game over
    while True:
        clear_screen()
        screen.blit(large_font.render("Peli päättyi!", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2 - 50))
        screen.blit(large_font.render(f"Pisteet: {game.state.score}", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2))
        screen.blit(large_font.render(f"Ennätys: {game.state.high_score}", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2 + 50))
        screen.blit(large_font.render("Paina Enter jatkaaksesi...", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 + 100))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return


def main():
    db = DatabaseManager(host="127.0.0.1", user="root", password="Python", database="flight_game")
    if not db.connect():
        print("Tietokantayhteys epäonnistui!")
        return

    player_id, username = login_or_register(db)
    if not player_id:
        return

    while True:
        choice = show_main_menu()
        if choice == "1":
            play_game(db, player_id, username)
        elif choice == "2":
            print("TODO: Omat tilastot")
        elif choice == "3":
            print("TODO: Top 10 lista")
        elif choice == "4":
            player_id, username = login_or_register(db)
        else:
            break

    db.close()


if __name__ == "__main__":
    main()

