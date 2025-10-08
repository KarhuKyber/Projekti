# database.py - MySQL-tietokantayhteydet ja kyselyt
from typing import List, Dict, Optional
import mysql.connector
import random


class DatabaseManager:
    """Hallinnoi MySQL-tietokantayhteyksiä ja kyselyitä"""

    def __init__(self, host="127.0.0.1", user="pythonUser", password="salasana", database="flight_game"):
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
            sql = """ SELECT score, game_mode, played_at
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
                    SELECT iso_country, name, continent, population, wikipedia_link, keywords
                    FROM country
                    WHERE iso_country NOT IN ({placeholders})
                    AND population IS NOT NULL
                    ORDER BY RAND()
                    LIMIT 1
                """
                kursori.execute(sql, tuple(exclude_codes))
            else:
                sql = """
                      SELECT iso_country, name, continent, population, wikipedia_link, keywords
                      FROM country
                      WHERE population IS NOT NULL
                      ORDER BY RAND() LIMIT 1 \
                      """
                kursori.execute(sql)

            rivi = kursori.fetchone()

            if rivi:
                return {
                    'iso_country': rivi[0],
                    'name': rivi[1],
                    'continent': rivi[2],
                    'population': rivi[3],
                    'wikipedia_link': rivi[4],
                    'keywords': rivi[5]
                }
            return None

        except mysql.connector.Error as err:
            print(f"Virhe tietokannassa: {err}")
            return None
        finally:
            kursori.close()


# game_logic.py - Pelin logiikka
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class QuestionType(Enum):
    """Kysymystyypit"""
    AIRPORT_ELEVATION = "elevation"
    COUNTRY_POPULATION = "population"


class GameMode(Enum):
    """Pelimoodit"""
    CLASSIC = "classic"
    SUDDEN_DEATH = "sudden_death"
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
    show_current_value: bool = False
    first_guess: bool = True


class GameEngine:
    """Pelin päälogiikka"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.state = GameState()
        self.used_ids = []
        self.used_country_codes = []

    def start_new_game(self, player_id: int, username: str, question_type: QuestionType,
                       game_mode: GameMode = GameMode.CLASSIC):
        """Aloittaa uuden pelin"""
        # Hae pelaajan ennätys
        high_score = self.db.get_player_high_score(player_id, game_mode.value)

        # Aseta elämät pelimuodon mukaan
        lives = 3 if game_mode == GameMode.CLASSIC else 1

        self.state = GameState(
            game_mode=game_mode,
            player_id=player_id,
            player_username=username,
            high_score=high_score,
            question_type=question_type,
            lives=lives
        )
        self.used_ids = []
        self.used_country_codes = []
        self.state.current_item = self._get_next_item()
        self.state.next_item = self._get_next_item()

    def _get_next_item(self) -> Optional[Dict]:
        """Hakee seuraavan kohteen kysymystyypistä riippuen"""
        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            item = self.db.get_random_airport(self.used_ids)
            if item:
                self.used_ids.append(item['id'])
            return item
        else:  # COUNTRY_POPULATION
            item = self.db.get_random_country(self.used_country_codes)
            if item:
                self.used_country_codes.append(item['iso_country'])
            return item

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
        elif self.state.question_type == QuestionType.COUNTRY_POPULATION:
            population = item.get('population')
            if population is None:
                return 0
            try:
                return float(population)
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

        # After first guess, always show the current value
        if self.state.first_guess:
            self.state.first_guess = False
            self.state.show_current_value = True

        if correct:
            self.state.score += 1
            message = f"Oikein! {self._format_item_name(self.state.next_item)}\n{self._format_value(next_value)}"

            # Tarkista uusi ennätys
            if self.state.score > self.state.high_score:
                self.state.high_score = self.state.score
                message += "\n🎉 UUSI ENNÄTYS! 🎉"

            # Move the correctly guessed item to current position
            self.state.current_item = self.state.next_item
            self.state.next_item = self._get_next_item()

            if self.state.score % 10 == 0:
                message += f"\n\nHienoa! {self.state.score} pistettä!"
        else:
            self.state.lives -= 1
            message = f"Väärin! {self._format_item_name(self.state.next_item)}\n{self._format_value(next_value)}"

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
                if self.state.game_mode == GameMode.SUDDEN_DEATH:
                    message += f"Äkkikuolema-tila: Yksi virhe riitti!\n"
                message += f"Ennätyksesi: {self.state.high_score}\n"
                message += f"{'=' * 50}"
            else:
                # Keep the current item but get a new one to compare against
                self.state.next_item = self._get_next_item()

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
        else:  # COUNTRY_POPULATION
            return item.get('name', 'Tuntematon')

    def _format_value(self, value: float) -> str:
        """Muotoilee arvon näyttämistä varten"""
        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            return f"Korkeus: {int(value):,} ft".replace(',', ' ')
        else:  # COUNTRY_POPULATION
            return f"Väkiluku: {int(value):,}".replace(',', ' ')

    def _get_question_description(self) -> str:
        """Palauttaa kysymyksen kuvauksen"""
        descriptions = {
            QuestionType.AIRPORT_ELEVATION: "Lentokentän korkeus merenpinnasta (ft)",
            QuestionType.COUNTRY_POPULATION: "Maan väkiluku",
        }
        return descriptions.get(self.state.question_type, "Tuntematon")

    def get_current_display(self) -> Dict:
        """Palauttaa näytettävät tiedot"""
        current_value = int(self._get_value(self.state.current_item))

        return {
            'score': self.state.score,
            'lives': self.state.lives,
            'current_item': self._format_item_name(self.state.current_item),
            'current_value': current_value,
            'current_value_formatted': self._format_value(current_value),
            'next_item': self._format_item_name(self.state.next_item),
            'question_type': self._get_question_description(),
            'game_over': self.state.game_over,
            'high_score': self.state.high_score,
            'player_username': self.state.player_username,
            'show_current_value': self.state.show_current_value,
            'first_guess': self.state.first_guess,
            'game_mode': self.state.game_mode
        }


# main.py - Pääohjelma
def clear_screen():
    """Tyhjentää konsolin (valinnainen)"""
    # Kommentoi pois jos et halua tyhjentää näyttöä
    # os.system('cls' if os.name == 'nt' else 'clear')
    pass


def show_game_mode_menu():
    """Näyttää pelimuodon valikon"""
    print("\n" + "=" * 60)
    print(" VALITSE PELIMUOTO ")
    print("=" * 60)
    print("1. Klassinen")
    print("   - 3 elämää, voit tehdä 2 virhettä")
    print("2. Äkkikuolema")
    print("   - 1 elämä, yksi virhe päättää pelin!")
    print("3. Takaisin päävalikkoon")

    while True:
        choice = input("\nValitse (1-3): ")
        if choice in ['1', '2', '3']:
            return choice
        print("Virheellinen valinta! Valitse 1, 2 tai 3.")


def show_question_type_menu():
    """Näyttää kysymystyypin valikon"""
    print("\n" + "=" * 60)
    print(" VALITSE KYSYMYSTYYPPI ")
    print("=" * 60)
    print("1. Lentokenttien korkeudet")
    print("   - Arvaa onko seuraavan lentokentän korkeus suurempi vai pienempi")
    print("2. Maiden väkiluvut")
    print("   - Arvaa onko seuraavan maan väkiluku suurempi vai pienempi")
    print("3. Takaisin päävalikkoon")

    while True:
        choice = input("\nValitse (1-3): ")
        if choice in ['1', '2', '3']:
            return choice
        print("Virheellinen valinta! Valitse 1, 2 tai 3.")


def show_main_menu():
    """Näyttää päävalikon"""
    print("\n" + "=" * 60)
    print(" PÄÄVALIKKO ")
    print("=" * 60)
    print("1. Pelaa")
    print("2. Omat tilastot")
    print("3. Pistetaulukko (Top 10)")
    print("4. Vaihda käyttäjää")
    print("5. Lopeta")
    return input("\nValitse (1-5): ")


def show_leaderboard(db: DatabaseManager, game_mode: str = 'classic'):
    """Näyttää pistetaulukon"""
    mode_name = "Klassinen" if game_mode == 'classic' else "Äkkikuolema"

    print("\n" + "=" * 60)
    print(f" PISTETAULUKKO - TOP 10 ({mode_name}) ")
    print("=" * 60)

    top_scores = db.get_top_scores(10, game_mode)

    if not top_scores:
        print("Ei vielä tuloksia!")
    else:
        for i, score in enumerate(top_scores, 1):
            date_str = score['played_at'].strftime('%d.%m.%Y %H:%M')
            print(f"{i:2}. {score['username']:20} {score['score']:4} pistettä  ({date_str})")

    input("\nPaina Enter palataksesi...")


def nayta_pelaajan_tilastot(db: DatabaseManager, player_id: int, username: str):
    """Näyttää pelaajan tilastot"""
    print("\n" + "=" * 60)
    print(f"TILASTOT - {username}")
    print("=" * 60)

    stats = db.get_player_statistics(player_id)

    print(f"\nPelatut pelit: {stats['games_played']}")
    print(f"Paras tulos: {stats['best_score']}")
    print(f"Keskiarvo: {stats['avg_score']}")
    print(f"Huonoin tulos: {stats['worst_score']}")

    print("\n" + "-" * 60)
    print("VIIMEISIMMÄT PELIT:")
    print("-" * 60)

    recent = db.get_player_recent_games(player_id, 5)
    if recent:
        for game in recent:
            mode_name = "Klassinen" if game['game_mode'] == 'classic' else "Äkkikuolema"
            date_str = game['played_at'].strftime('%d.%m.%Y %H:%M')
            print(f"{game['score']:4} pistettä  ({mode_name})  ({date_str})")
    else:
        print("Ei vielä pelattuja pelejä!")

    input("\nPaina Enter palataksesi...")


def login_or_register(db: DatabaseManager) -> tuple[int, str]:
    """Kirjautuminen tai rekisteröityminen"""
    print("\n" + "=" * 60)
    print("KIRJAUTUMINEN")
    print("=" * 60)

    while True:
        username = input("\nAnna käyttäjänimesi (tai 'q' lopettaaksesi): ").strip()

        if username.lower() == 'q':
            return None, None

        if not username:
            print("Käyttäjänimi ei voi olla tyhjä!")
            continue

        if len(username) < 3:
            print("Käyttäjänimen pitää olla vähintään 3 merkkiä!")
            continue

        player_id = db.get_or_create_player(username)

        if player_id:
            player = db.get_player_by_username(username)
            if player:
                print(f"\nTervetuloa takaisin, {username}!")
                return player_id, username
        else:
            print("Virhe käyttäjän luonnissa. Yritä toista nimeä.")


def main():
    """Pääohjelma"""

    print("=" * 60)
    print("HIGHER OR LOWER - Lentokentät ja maat")
    print("=" * 60)
    print("\nYhdistetään tietokantaan...")

    db = DatabaseManager(
        host="127.0.0.1",
        user="pythonUser",
        password="salasana",
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
            # Pelimuodon valinta
            while True:
                game_mode_choice = show_game_mode_menu()

                if game_mode_choice == '1':
                    game_mode = GameMode.CLASSIC
                    break
                elif game_mode_choice == '2':
                    game_mode = GameMode.SUDDEN_DEATH
                    break
                elif game_mode_choice == '3':
                    break

            if game_mode_choice == '3':
                continue  # Takaisin päävalikkoon

            # Kysymystyypin valinta
            while True:
                question_choice = show_question_type_menu()

                if question_choice == '1':
                    question_type = QuestionType.AIRPORT_ELEVATION
                    break
                elif question_choice == '2':
                    question_type = QuestionType.COUNTRY_POPULATION
                    break
                elif question_choice == '3':
                    break

            if question_choice == '3':
                continue  # Takaisin päävalikkoon

            # Pelaa
            print("\n" + "=" * 60)
            if question_type == QuestionType.AIRPORT_ELEVATION:
                print(" LENTOKENTTIEN KORKEUDET ")
            else:
                print(" MAIDEN VÄKILUVUT ")
            print("=" * 60)

            if game_mode == GameMode.CLASSIC:
                print("Klassinen tila - 3 elämää")
                print("Arvaa, onko seuraava arvo HIGHER (suurempi) vai LOWER (pienempi)!")
                print("Sinulla on 3 elämää. Onnea matkaan!\n")
            else:
                print("ÄKKIKUOLEMA - 1 elämä!")
                print("Arvaa, onko seuraava arvo HIGHER (suurempi) vai LOWER (pienempi)!")
                print("Yksi virhe päättää pelin! Onnea matkaan!\n")

            input("Paina Enter aloittaaksesi...")

            game.start_new_game(player_id, username, question_type, game_mode)

            if not game.state.current_item or not game.state.next_item:
                print("\nVirhe: Ei voitu hakea tietoja!")
                continue

            while not game.state.game_over:
                display = game.get_current_display()

                print("\n" + "-" * 60)
                mode_text = "Klassinen" if display['game_mode'] == GameMode.CLASSIC else "Äkkikuolema"
                lives_display = '❤️' * display['lives'] if display['game_mode'] == GameMode.CLASSIC else '💀'

                print(
                    f"Pelaaja: {display['player_username']} | Pisteet: {display['score']} | Ennätys: {display['high_score']} | Elämät: {lives_display} ({mode_text})")
                print(f"Kysymystyyppi: {display['question_type']}")
                print("-" * 60)
                print(f"\nNykyinen: {display['current_item']}")

                # Show current value only after first guess
                if display['show_current_value']:
                    print(f"{display['current_value_formatted']}")
                else:
                    if question_type == QuestionType.AIRPORT_ELEVATION:
                        print(f"Korkeus: ???")
                    else:
                        print(f"Väkiluku: ???")

                print(f"\nSeuraava: {display['next_item']}")
                if question_type == QuestionType.AIRPORT_ELEVATION:
                    print(f"Korkeus: ???")
                else:
                    print(f"Väkiluku: ???")

                while True:
                    choice = input("\nOnko seuraava HIGHER vai LOWER? (h/l) tai (q lopettaaksesi): ").lower()
                    if choice in ['h', 'l', 'q']:
                        break
                    print("Virheellinen valinta!")

                if choice == 'q':
                    print("\nLopetetaan peli...")
                    break

                is_higher = choice == 'h'
                correct, message = game.make_guess(is_higher)

                print(f"\n{'✓' if correct else '✗'} {message}")

                if not correct and not game.state.game_over:
                    input("\nPaina Enter jatkaaksesi...")

            if game.state.game_over:
                input("\nPaina Enter palataksesi valikkoon...")

        elif choice == '2':
            # Omat tilastot
            nayta_pelaajan_tilastot(db, player_id, username)

        elif choice == '3':
            # Pistetaulukko - kysy pelimuoto
            print("\nValitse pistetaulukon pelimuoto:")
            print("1. Klassinen")
            print("2. Äkkikuolema")
            leaderboard_choice = input("\nValitse (1-2) tai Enter palataksesi: ")

            if leaderboard_choice == '1':
                show_leaderboard(db, 'classic')
            elif leaderboard_choice == '2':
                show_leaderboard(db, 'sudden_death')
            else:
                continue

        elif choice == '4':
            # Vaihda käyttäjää
            player_id, username = login_or_register(db)
            if not player_id:
                break

        elif choice == '5':
            # Lopeta
            print("\nKiitos pelaamisesta! Näkemiin!")
            break

        else:
            print("Virheellinen valinta!")

    db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPeli keskeytetty. Näkemiin!")
    except Exception as e:
        print(f"\nVirhe: {e}")
        import traceback

        traceback.print_exc()