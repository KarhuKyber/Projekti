# database.py - MySQL-tietokantayhteydet ja kyselyt
import mysql.connector
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import random
pygame.init()
screen = pygame.display.set_mode((1280, 720))


class DatabaseManager:
    """Hallinnoi MySQL-tietokantayhteyksiä ja kyselyitä"""

    def __init__(self, host="127.0.0.1", user="root", password="Python", database="flight_game"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        """Avaa yhteys MySQL-tietokantaan"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("Yhteys tietokantaan muodostettu!")
            return self.connection
        except mysql.connector.Error as err:
            print(f"Virhe tietokantayhteydessä: {err}")
            return None

    def close(self):
        """Sulkee tietokantayhteyden"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Tietokantayhteys suljettu.")

    # KÄYTTÄJÄHALLINTA

    def create_player(self, username: str) -> Optional[int]:
        """Luo uuden pelaajan"""
        kursori = self.connection.cursor()

        try:
            sql = "INSERT INTO players (username) VALUES (%s)"
            kursori.execute(sql, (username,))
            self.connection.commit()
            return kursori.lastrowid
        except mysql.connector.IntegrityError:
            print(f"Käyttäjänimi '{username}' on jo olemassa!")
            return None
        except mysql.connector.Error as err:
            print(f"Virhe pelaajan luonnissa: {err}")
            return None
        finally:
            kursori.close()

    def get_player_by_username(self, username: str) -> Optional[Dict]:
        """Hakee pelaajan käyttäjänimellä"""
        kursori = self.connection.cursor()

        try:
            sql = "SELECT id, username, created_at FROM players WHERE username = %s"
            kursori.execute(sql, (username,))
            rivi = kursori.fetchone()

            if rivi:
                return {
                    'id': rivi[0],
                    'username': rivi[1],
                    'created_at': rivi[2]
                }
            return None

        except mysql.connector.Error as err:
            print(f"Virhe pelaajan haussa: {err}")
            return None
        finally:
            kursori.close()

    def get_or_create_player(self, username: str) -> Optional[int]:
        """Hakee pelaajan tai luo uuden jos ei löydy"""
        player = self.get_player_by_username(username)
        if player:
            return player['id']
        return self.create_player(username)

    # HIGH SCORE -HALLINTA

    def save_score(self, player_id: int, score: int, game_mode: str = 'classic') -> bool:
        """Tallentaa pelaajan pisteet"""
        kursori = self.connection.cursor()

        try:
            sql = "INSERT INTO high_scores (player_id, score, game_mode) VALUES (%s, %s, %s)"
            kursori.execute(sql, (player_id, score, game_mode))
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Virhe pisteiden tallennuksessa: {err}")
            return False
        finally:
            kursori.close()

    def get_player_high_score(self, player_id: int, game_mode: str = 'classic') -> int:
        """Hakee pelaajan parhaan tuloksen"""
        kursori = self.connection.cursor()

        try:
            sql = """
                  SELECT MAX(score)
                  FROM high_scores
                  WHERE player_id = %s \
                    AND game_mode = %s \
                  """
            kursori.execute(sql, (player_id, game_mode))
            rivi = kursori.fetchone()
            return rivi[0] if rivi and rivi[0] is not None else 0
        except mysql.connector.Error as err:
            print(f"Virhe high scoren haussa: {err}")
            return 0
        finally:
            kursori.close()

    def get_player_statistics(self, player_id: int) -> Dict:
        """Hakee pelaajan tilastot"""
        kursori = self.connection.cursor()

        try:
            sql = """
                  SELECT COUNT(*)   as games_played, \
                         MAX(score) as best_score, \
                         AVG(score) as avg_score, \
                         MIN(score) as worst_score
                  FROM high_scores
                  WHERE player_id = %s \
                  """
            kursori.execute(sql, (player_id,))
            rivi = kursori.fetchone()

            if rivi:
                return {
                    'games_played': rivi[0] or 0,
                    'best_score': rivi[1] or 0,
                    'avg_score': round(rivi[2], 1) if rivi[2] else 0,
                    'worst_score': rivi[3] or 0
                }
            return {'games_played': 0, 'best_score': 0, 'avg_score': 0, 'worst_score': 0}

        except mysql.connector.Error as err:
            print(f"Virhe tilastojen haussa: {err}")
            return {'games_played': 0, 'best_score': 0, 'avg_score': 0, 'worst_score': 0}
        finally:
            kursori.close()

    def get_top_scores(self, limit: int = 10, game_mode: str = 'classic') -> List[Dict]:
        """Hakee parhaat tulokset"""
        kursori = self.connection.cursor()

        try:
            sql = """
                  SELECT p.username, h.score, h.played_at
                  FROM high_scores h
                           JOIN players p ON h.player_id = p.id
                  WHERE h.game_mode = %s
                  ORDER BY h.score DESC
                      LIMIT %s \
                  """
            kursori.execute(sql, (game_mode, limit))
            rivit = kursori.fetchall()

            return [
                {
                    'username': rivi[0],
                    'score': rivi[1],
                    'played_at': rivi[2]
                }
                for rivi in rivit
            ]

        except mysql.connector.Error as err:
            print(f"Virhe top scores -haussa: {err}")
            return []
        finally:
            kursori.close()

    def get_player_recent_games(self, player_id: int, limit: int = 5) -> List[Dict]:
        """Hakee pelaajan viimeisimmät pelit"""
        kursori = self.connection.cursor()

        try:
            sql = """
                  SELECT score, game_mode, played_at
                  FROM high_scores
                  WHERE player_id = %s
                  ORDER BY played_at DESC
                      LIMIT %s \
                  """
            kursori.execute(sql, (player_id, limit))
            rivit = kursori.fetchall()

            return [
                {
                    'score': rivi[0],
                    'game_mode': rivi[1],
                    'played_at': rivi[2]
                }
                for rivi in rivit
            ]

        except mysql.connector.Error as err:
            print(f"Virhe pelihistorian haussa: {err}")
            return []
        finally:
            kursori.close()

    # LENTOKENTTÄ- JA MAATIEDOT

    def get_random_airport(self, exclude_ids: List[int] = None) -> Optional[Dict]:
        """Hakee satunnaisen lentokentän"""
        if not self.connection or not self.connection.is_connected():
            print("Ei yhteyttä tietokantaan!")
            return None

        kursori = self.connection.cursor()

        try:
            if exclude_ids and len(exclude_ids) > 0:
                placeholders = ','.join(['%s'] * len(exclude_ids))
                sql = f"""
                    SELECT a.id, a.ident, a.type, a.name, a.latitude_deg, 
                           a.longitude_deg, a.elevation_ft, a.continent, 
                           a.iso_country, a.municipality, c.name as country_name
                    FROM airport a
                    LEFT JOIN country c ON a.iso_country = c.iso_country
                    WHERE a.id NOT IN ({placeholders})
                    AND a.type IN ('large_airport', 'medium_airport')
                    ORDER BY RAND()
                    LIMIT 1
                """
                kursori.execute(sql, tuple(exclude_ids))
            else:
                sql = """
                      SELECT a.id, \
                             a.ident, \
                             a.type, \
                             a.name, \
                             a.latitude_deg,
                             a.longitude_deg, \
                             a.elevation_ft, \
                             a.continent,
                             a.iso_country, \
                             a.municipality, \
                             c.name as country_name
                      FROM airport a
                               LEFT JOIN country c ON a.iso_country = c.iso_country
                      WHERE a.type IN ('large_airport', 'medium_airport')
                      ORDER BY RAND() LIMIT 1 \
                      """
                kursori.execute(sql)

            rivi = kursori.fetchone()

            if rivi:
                return {
                    'id': rivi[0],
                    'ident': rivi[1],
                    'type': rivi[2],
                    'name': rivi[3],
                    'latitude_deg': rivi[4],
                    'longitude_deg': rivi[5],
                    'elevation_ft': rivi[6],
                    'continent': rivi[7],
                    'iso_country': rivi[8],
                    'municipality': rivi[9],
                    'country_name': rivi[10]
                }
            return None

        except mysql.connector.Error as err:
            print(f"Virhe tietokannassa: {err}")
            return None
        finally:
            kursori.close()

    def get_random_country(self, exclude_codes: List[str] = None) -> Optional[Dict]:
        """Hakee satunnaisen maan"""
        if not self.connection or not self.connection.is_connected():
            print("Ei yhteyttä tietokantaan!")
            return None

        kursori = self.connection.cursor()

        try:
            if exclude_codes and len(exclude_codes) > 0:
                placeholders = ','.join(['%s'] * len(exclude_codes))
                sql = f"""
                    SELECT iso_country, name, continent, wikipedia_link, keywords
                    FROM country
                    WHERE iso_country NOT IN ({placeholders})
                    ORDER BY RAND()
                    LIMIT 1
                """
                kursori.execute(sql, tuple(exclude_codes))
            else:
                sql = """
                      SELECT iso_country, name, continent, wikipedia_link, keywords
                      FROM country
                      ORDER BY RAND() LIMIT 1 \
                      """
                kursori.execute(sql)

            rivi = kursori.fetchone()

            if rivi:
                return {
                    'iso_country': rivi[0],
                    'name': rivi[1],
                    'continent': rivi[2],
                    'wikipedia_link': rivi[3],
                    'keywords': rivi[4]
                }
            return None

        except mysql.connector.Error as err:
            print(f"Virhe tietokannassa: {err}")
            return None
        finally:
            kursori.close()


# game_logic.py - Pelin logiikka



# Margins
    MARGIN_LEFT = 230
    MARGIN_TOP = 150
 
    # WINDOW SIZE
    WIDTH = 800
    HEIGHT = 600
 
    # COLORS
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (110, 110, 110)
    GREEN = (0, 255, 0)
    LIGHT_GREEN = (0, 120, 0)
    RED = (255, 0, 0)
    LIGHT_RED = (120, 0, 0)
 
    
    
    # Initializing PyGame
    pygame.init()
 
 
    # Setting up the screen and background
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    screen.fill(GRAY)
 
    # Setting up caption
    pygame.display.set_caption("Hi-Lo Game")
 
   
    
 
    # Types of fonts to be used
    small_font = pygame.font.Font(None, 32)
    large_font = pygame.font.Font(None, 50)
 
    # Hign and Low Game Buttons
    high_button = large_font.render("HIGH", True, WHITE)
 
    # Gets_rectangular covering of text
    high_button_rect = high_button.get_rect()
 
    # Places the text
    high_button_rect.center = (280, 400)
 
    low_button = large_font.render("LOW", True, WHITE)
    low_button_rect = low_button.get_rect()
    low_button_rect.center = (520, 400)
    
    pelaa = large_font.render("pelaa", true, white)
    pelaa_rect = pelaa.get_rect()
    pelaa_rect.center=(200, 200)
    # omat tilastot
    omat_tilastot = large_font.render("omat tilastot", true, white)
    omat_tilastot_rect = omat_tilastot.get_rect()
    omat_tilastot_rect.center=(400, 200)
    #kirjaudu sisään
    kirjaudu_sisaan = large_font.render("kirjaudu sisään", true, white)
    kirjaudu_sisaan_rect = kirjaudu_sisaan.get_rect()
    kirjaudu_sisaan_rect.center=(600, 200)
    #top 10
    top_10 = large_font.render("top 10", true, white)
    top_10_rect = top_10.get_rect()
    top_10_rect.center=(800, 200)



class QuestionType(Enum):
    """Kysymystyypit"""
    AIRPORT_ELEVATION = "elevation"


class GameMode(Enum):
    """Pelimoodit"""
    CLASSIC = "classic"
    TIME_ATTACK = "time_attack"
    CHALLENGE = "challenge"


@dataclass
class GameState:
    """Pelin tila"""
    score: int = 0
    lives: int = 3
    current_item: Optional[Dict] = None
    next_item: Optional[Dict] = None
    question_type: Optional[QuestionType] = None
    game_over: bool = False
    high_score: int = 0
    game_mode: GameMode = GameMode.CLASSIC
    player_id: Optional[int] = None
    player_username: str = ""


class GameEngine:
    """Pelin päälogiikka"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.state = GameState()
        self.used_ids = []

    def start_new_game(self, player_id: int, username: str, game_mode: GameMode = GameMode.CLASSIC):
        """Aloittaa uuden pelin"""
        # Hae pelaajan ennätys
        high_score = self.db.get_player_high_score(player_id, game_mode.value)

        self.state = GameState(
            game_mode=game_mode,
            player_id=player_id,
            player_username=username,
            high_score=high_score
        )
        self.used_ids = []
        self.state.question_type = self._select_question_type()
        self.state.current_item = self._get_next_item()
        self.state.next_item = self._get_next_item()

    def _select_question_type(self) -> QuestionType:
        """Valitsee satunnaisen kysymystyypin"""
        return QuestionType.AIRPORT_ELEVATION

    def _get_next_item(self) -> Optional[Dict]:
        """Hakee seuraavan kohteen kysymystyypistä riippuen"""
        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            item = self.db.get_random_airport(self.used_ids)
            if item:
                self.used_ids.append(item['id'])
            return item
        else:
            return self.db.get_random_country()

    def _get_value(self, item: Dict) -> float:
        """Palauttaa vertailtavan arvon kysymystyypistä riippuen"""
        if not item:
            return 0

        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            elevation = item.get('elevation_ft')
            if elevation is None:
                return 0
            try:
                return float(elevation)
            except (ValueError, TypeError):
                return 0

        return 0

    def make_guess(self, is_higher: bool) -> tuple[bool, str]:
        """Käsittelee pelaajan arvauksen"""
        if self.state.game_over:
            return False, "Peli on päättynyt!"

        current_value = self._get_value(self.state.current_item)
        next_value = self._get_value(self.state.next_item)

        correct = (is_higher and next_value >= current_value) or \
                  (not is_higher and next_value <= current_value)

        if correct:
            self.state.score += 1
            message = f"Oikein! {self._format_item_name(self.state.next_item)}\nKorkeus: {int(next_value)} ft"

            # Tarkista uusi ennätys
            if self.state.score > self.state.high_score:
                self.state.high_score = self.state.score
                message += "\n🎉 UUSI ENNÄTYS! 🎉"

            self.state.current_item = self.state.next_item
            self.state.next_item = self._get_next_item()

            if self.state.score % 10 == 0:
                message += f"\n\nHienoa! {self.state.score} pistettä!"
        else:
            self.state.lives -= 1
            message = f"Väärin! {self._format_item_name(self.state.next_item)}\nKorkeus: {int(next_value)} ft"

            if self.state.lives <= 0:
                self.state.game_over = True
                # Tallenna tulos tietokantaan
                if self.state.player_id:
                    self.db.save_score(
                        self.state.player_id,
                        self.state.score,
                        self.state.game_mode.value
                    )
                message += f"\n\n{'=' * 50}\nPELI PÄÄTTYI!\n"
                message += f"Pistemäärä: {self.state.score}\n"
                message += f"Ennätyksesi: {self.state.high_score}\n"
                message += f"{'=' * 50}"

        return correct, message

    def _format_item_name(self, item: Dict) -> str:
        """Muotoilee kohteen nimen"""
        if not item:
            return "Tuntematon"

        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            name = item.get('name', 'Tuntematon')
            country = item.get('country_name', '')
            municipality = item.get('municipality', '')

            if municipality and country:
                return f"{name}\n({municipality}, {country})"
            elif country:
                return f"{name}\n({country})"
            else:
                return name
        else:
            return item.get('name', 'Tuntematon')

    def _get_question_description(self) -> str:
        """Palauttaa kysymyksen kuvauksen"""
        descriptions = {
            QuestionType.AIRPORT_ELEVATION: "Lentokentän korkeus merenpinnasta (ft)",
        }
        return descriptions.get(self.state.question_type, "Tuntematon")

    def get_current_display(self) -> Dict:
        """Palauttaa näytettävät tiedot"""
        return {
            'score': self.state.score,
            'lives': self.state.lives,
            'current_item': self._format_item_name(self.state.current_item),
            'current_value': int(self._get_value(self.state.current_item)),
            'next_item': self._format_item_name(self.state.next_item),
            'question_type': self._get_question_description(),
            'game_over': self.state.game_over,
            'high_score': self.state.high_score,
            'player_username': self.state.player_username
        }


# main.py - Pääohjelma
def clear_screen():
    #tyhjentää näytön
    screen.fill(GRAY)
    pygame.display.update()


def show_main_menu():
    # Näyttää päävalikon
    clear_screen()
    pygame.draw.rect(screen, GREEN, [200, 150, 150, 50])
    screen.blit(pelaa, pelaa_rect)
    pygame.draw.rect(screen, GREEN, [400, 150, 200, 50])
    screen.blit(omat_tilastot, omat_tilastot_rect)
    pygame.draw.rect(screen, GREEN, [600, 150, 250, 50])
    screen.blit(kirjaudu_sisaan, kirjaudu_sisaan_rect)
    pygame.draw.rect(screen, GREEN, [800, 150, 100, 50])
    screen.blit(top_10, top_10_rect)
    pygame.display.update()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if pelaa_rect.collidepoint(event.pos):
                return '1'
            elif omat_tilastot_rect.collidepoint(event.pos):
                return '2'
            elif top_10_rect.collidepoint(event.pos):
                return '3'
            elif kirjaudu_sisaan_rect.collidepoint(event.pos):
                return '4'

    
def show_leaderboard(db: DatabaseManager):
    # Näyttää pistetaulukon
    clear_screen()
    pygame.draw.rect(screen, GREEN, [100, 100, 600, 400])
    d_top = large_font.render("Pistetaulukko", True, white)
    d_top_rect = d_top.get_rect(center=(screen.get_width() / 2, 50))
    screen.blit(d_top, d_top_rect)

    top_scores = db.get_top_scores(10)

    if not top_scores:
        tulokset = small_font.render("Ei vielä tallennettuja pisteitä.", True, white)
        tulokset_rect = tulokset.get_rect(topleft=(120, 100))
        screen.blit(tulokset, tulokset_rect)
        pygame.display.update()
    else:
        for i, score in enumerate(top_scores, 1):
            date_str = score['played_at'].strftime('%d.%m.%Y %H:%M')
            tulokset = small_font.render(f"{i}. {score['username']:15} {score['score']:4} pistettä  ({date_str})", True, white)
            tulokset_rect = tulokset.get_rect(topleft=(120, 100 + i * 30))
            screen.blit(tulokset, tulokset_rect) 
        pygame.display.update()
 


def show_player_stats(db: DatabaseManager, player_id: int, username: str):
    """Näyttää pelaajan tilastot"""
    clear_screen()
    pygame.draw.rect(screen, GREEN, [100, 100, 600, 400])
    d_top = large_font.render("Omat tilastot", True, white)
    d_top_rect = d_top.get_rect(center=(screen.get_width() / 2, 50))
    screen.blit(d_top, d_top_rect)
    stats = db.get_player_statistics(player_id)
    

    recent = db.get_player_recent_games(player_id, 5)
    if recent:
        for game in recent:
            date_str = game['played_at'].strftime('%d.%m.%Y %H:%M')
            pelit = small_font.render(f"{game['score']:4} pistettä  ({date_str})", True, white)
            pelit_rect = pelit.get_rect(topleft=(120, 250 + recent.index(game) * 30))
            screen.blit(pelit, pelit_rect)
        pygame.display.update()
            
    else:
        pelit = small_font.render("Ei vielä pelejä pelattu.", True, white)
        pelit_rect = pelit.get_rect(topleft=(120, 250))
        screen.blit(pelit, pelit_rect)
        pygame.display.update()

    if stats['games_played'] == 0:
        stats_text = "Ei vielä pelejä pelattu."
        stats_render = small_font.render(stats_text, True, white)
        stats_rect = stats_render.get_rect(topleft=(120, 100))
        screen.blit(stats_render, stats_rect)
        pygame.display.update()
        pygame.time.delay(2000)


def login_or_register(db: DatabaseManager) -> tuple[int, str]:
    """Kirjautuminen tai rekisteröityminen"""
    clear_screen ()
    pygame.draw.rect(screen, GREEN, [100, 100, 600, 400])
    d_top = large_font.render("Kirjaudu sisään tai rekisteröidy", True, white)
    d_top_rect = d_top.get_rect(center=(screen.get_width() / 2, 50))
    screen.blit(d_top, d_top_rect)
    pygame.display.update()
    user_text = ''
    base_font = pygame.font.Font(None, 32)
    input_rect = pygame.Rect(300, 200, 140, 32)
    color = pygame.Color('lightskyblue3')

    while True:

            
        if event.type == pygame.KEYDOWN:
            # Check for backspace
            if event.key == pygame.K_BACKSPACE:

                # get text input from 0 to -1 i.e. end.
                user_text = user_text[:-1]

            # Unicode standard is used for string
            # formation
            else:
                user_text += event.unicode
        # draw rectangle and argument passed which should
        # be on screen
        pygame.draw.rect(screen, color, input_rect)

        text_surface = base_font.render(user_text, True, (255, 255, 255))

        # render at position stated in arguments
        screen.blit(text_surface, (input_rect.x+5, input_rect.y+5))

        # set width of textfield so that text cannot get
        # outside of user's text input
        input_rect.w = max(100, text_surface.get_width()+10)

        # display.flip() will update only a portion of the
        # screen to updated, not full area
        pygame.display.flip()

        if user_text.lower() == 'q':
            return None, None

        if not username:
            pd_top = large_font.render("käyttäjänimi ei voi olla tyhjä", True, white)
            pygame.display.flip()
            continue

            

        if len(username) < 3:
            d_top = large_font.render("Käyttäjänimen pitää olla vähintään 3 merkkiä", True, white)
            pygame.display.flip()
            continue

        player_id = db.get_or_create_player(username)

        if player_id:
            player = db.get_player_by_username(username)
            if player:
                clear_screen()
                pygame.draw.rect(screen, GREEN, [100, 100, 600, 400])
                tervetuloa = large_font.render(f"Tervetuloa, {player['username']}!", True, white)
                tervetuloa_rect = tervetuloa.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2))
                screen.blit(tervetuloa, tervetuloa_rect)
                pygame.display.update()
                return player_id, username
        else:
            print("Virhe käyttäjän luonnissa. Yritä toista nimeä.")


def main():
    """Pääohjelma"""
    clear_screen()
    screen.fill(GRAY)
    screen.blit(large_font.render("Lentokenttä Hi-Lo Peli", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 - 50)) 
    pygame.display.flip()

    # Yhdistä tietokantaan


   

    db = DatabaseManager(
        host="127.0.0.1",
        user="root",
        password="Python",
        database="flight_game"
    )

    if not db.connect():
        print("\nVirhe: Tietokantayhteys epäonnistui!")
        return

    # Kirjautuminen
    player_id, username = login_or_register(db)
    if not player_id:
        db.close()
        return

    game = GameEngine(db)

    # Pääsilmukka
    while True:
        choice = show_main_menu()

        if choice == '1':
            # Aloita uusi peli
            clear_screen()
            screen.fill(GRAY)
            screen.blit(large_font.render("Arvaa, onko seuraava arvo HIGHER (suurempi) vai LOWER (pienempi)!", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 - 50))
            screen.blit(large_font.render("Sinulla on 3 elämää. Jokainen väärä arvaus menettää yhden.", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 - 30))
            screen.blit(large_font.render("Paina välilyöntiä aloittaaksesi...", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 + 10))   
            pygame.display.flip()


            game.start_new_game(player_id, username)

            if not game.state.current_item or not game.state.next_item:
                print("\nVirhe: Ei voitu hakea lentokenttätietoja!")
                continue
            if event.key == pygame.K_SPACE:
                
                while not game.state.game_over:
                    display = game.get_current_display()
                    clear_screen() 
                    screen.fill(GRAY)
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
                    pygame.display.flip()

                    while True:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                pygame.quit()
                                return
                            if event.type == pygame.MOUSEBUTTONDOWN:
                                if high_button_rect.collidepoint(event.pos):
                                    choice = 'h'
                                elif low_button_rect.collidepoint(event.pos):
                                    choice = 'l'
                                else:
                                    continue
                            if event.type == pygame.KEYDOWN:
                                if event.key == pygame.K_h:
                                    choice = 'h'
                                elif event.key == pygame.K_l:
                                    choice = 'l'
                                elif event.key == pygame.K_q:
                                    choice = 'q'
                                else:
                                    continue
                            if choice in ['h', 'l', 'q']:
                                break


                        if choice == 'q':
                            print("\nLopetetaan peli...")
                            break

                        is_higher = choice == 'h'
                        correct, message = game.make_guess(is_higher)
                        display = game.get_current_display()
                        clear_screen() 
                        screen.fill(GRAY)
                        screen.blit(large_font.render(f"", True, WHITE), (50, 20))

                        if not correct and not game.state.game_over:
                            screen.blit(large_font.render("Väärin!", True, RED), (WIDTH // 2 - 100, HEIGHT // 2 - 50))
                            pygame.display.flip()
                            pygame.time.delay(2000)  # Näytä "Väärin!" 2 sekuntia
                            break

            if game.state.game_over:
                while True:
                    clear_screen()
                    screen.fill(GRAY)
                    screen.blit(large_font.render("Peli päättyi!", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2 - 50))
                    screen.blit(large_font.render(f"Pistemäärä: {display['score']}", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2))
                    screen.blit(large_font.render(f"Ennätyksesi: {display['high_score']}", True, WHITE), (WIDTH // 2 - 100, HEIGHT // 2 + 50))
                    screen.blit(large_font.render("Paina Enter palataksesi päävalikkoon...", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 + 100))
                    pygame.display.flip()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_RETURN:
                                choice = 'enter'
                                break

        elif choice == '2':
            # Omat tilastot
            show_player_stats(db, player_id, username)

        elif choice == '3':
            # Pistetaulukko
            show_leaderboard(db)

        elif choice == '4':
            # Vaihda käyttäjää
            player_id, username = login_or_register(db)
            if not player_id:
                break

        elif choice == '5':
            # Lopeta
            clear_screen()
            screen.fill(GRAY)
            screen.blit(large_font.render("Kiitos pelaamisesta! Näkemiin!", True, WHITE), (WIDTH // 2 - 200, HEIGHT // 2 - 50))
            pygame.display.update()
            break

        else:
            print("Virheellinen valinta!")

    db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPeli keskeytetty. Näkemiin!")
    except Exception as e:
        print(f"\nVirhe: {e}")
        import traceback


        traceback.print_exc()


