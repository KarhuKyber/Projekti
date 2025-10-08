
import mysql.connector
import time
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


class QuestionType(Enum):
    """Kysymystyypit"""
    AIRPORT_ELEVATION = "elevation"
    COUNTRY_POPULATION = "population"


class GameMode(Enum):
    """Pelimoodit"""
    CLASSIC = "classic"
    SUDDEN_DEATH = "sudden_death"
    TIME_ATTACK = "time_attack"


@dataclass
class GameSettings:
    """Pelin asetukset"""
    LIVES_CLASSIC = 3
    LIVES_OTHER = 1
    TIME_ATTACK_DURATION = 60.0


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
    time_remaining: float = 0
    start_time: float = 0



class DatabaseManager:
    """Hallinnoi MySQL-tietokantayhteyksiä ja kyselyitä"""

    def __init__(self, host="127.0.0.1", user="pythonUser", password="salasana", database="flight_game"):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None

    def connect(self) -> bool:
        """Avaa yhteys MySQL-tietokantaan"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            print("Yhteys tietokantaan muodostettu!")
            return True
        except mysql.connector.Error as err:
            print(f"Virhe tietokantayhteydessä: {err}")
            return False

    def close(self):
        """Sulkee tietokantayhteyden"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Tietokantayhteys suljettu.")

    def _execute_query(self, query: str, params: Tuple = None) -> List:
        """Suorittaa SQL-kyselyn ja palauttaa tulokset"""
        if not self.connection:
            print("Ei yhteyttä tietokantaan!")
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Virhe tietokantakyselyssä: {err}")
            return []
        finally:
            cursor.close()

    def _execute_update(self, query: str, params: Tuple = None) -> bool:
        """Suorittaa SQL-päivityksen"""
        if not self.connection:
            print("Ei yhteyttä tietokantaan!")
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Virhe tietokantapäivityksessä: {err}")
            return False
        finally:
            cursor.close()

    # KÄYTTÄJÄHALLINTA

    def create_player(self, username: str) -> Optional[int]:
        """Luo uuden pelaajan"""
        try:
            sql = "INSERT INTO players (username) VALUES (%s)"
            if self._execute_update(sql, (username,)):
                cursor = self.connection.cursor()
                cursor.execute("SELECT LAST_INSERT_ID()")
                return cursor.fetchone()[0]
            return None
        except mysql.connector.IntegrityError:
            print(f"Käyttäjänimi '{username}' on jo olemassa!")
            return None

    def get_player_by_username(self, username: str) -> Optional[Dict]:
        """Hakee pelaajan käyttäjänimellä"""
        sql = "SELECT id, username, created_at FROM players WHERE username = %s"
        result = self._execute_query(sql, (username,))

        if result:
            return {
                'id': result[0][0],
                'username': result[0][1],
                'created_at': result[0][2]
            }
        return None

    def get_or_create_player(self, username: str) -> Optional[int]:
        """Hakee pelaajan tai luo uuden jos ei löydy"""
        player = self.get_player_by_username(username)
        return player['id'] if player else self.create_player(username)

    # HIGH SCORE -HALLINTA

    def save_score(self, player_id: int, score: int, game_mode: str = 'classic') -> bool:
        """Tallentaa pelaajan pisteet"""
        sql = "INSERT INTO high_scores (player_id, score, game_mode) VALUES (%s, %s, %s)"
        return self._execute_update(sql, (player_id, score, game_mode))

    def get_player_high_score(self, player_id: int, game_mode: str = 'classic') -> int:
        """Hakee pelaajan parhaan tuloksen"""
        sql = "SELECT MAX(score) FROM high_scores WHERE player_id = %s AND game_mode = %s"
        result = self._execute_query(sql, (player_id, game_mode))
        return result[0][0] if result and result[0][0] is not None else 0

    def get_player_statistics(self, player_id: int) -> Dict:
        """Hakee pelaajan tilastot"""
        sql = """
              SELECT COUNT(*)   as games_played, \
                     MAX(score) as best_score,
                     AVG(score) as avg_score, \
                     MIN(score) as worst_score
              FROM high_scores \
              WHERE player_id = %s \
              """
        result = self._execute_query(sql, (player_id,))

        if result and result[0]:
            return {
                'games_played': result[0][0] or 0,
                'best_score': result[0][1] or 0,
                'avg_score': round(result[0][2], 1) if result[0][2] else 0,
                'worst_score': result[0][3] or 0
            }
        return {'games_played': 0, 'best_score': 0, 'avg_score': 0, 'worst_score': 0}

    def get_top_scores(self, limit: int = 10, game_mode: str = 'classic') -> List[Dict]:
        """Hakee parhaat tulokset"""
        sql = """
              SELECT p.username, h.score, h.played_at
              FROM high_scores h
                       JOIN players p ON h.player_id = p.id
              WHERE h.game_mode = %s
              ORDER BY h.score DESC
                  LIMIT %s \
              """
        results = self._execute_query(sql, (game_mode, limit))

        return [
            {
                'username': row[0],
                'score': row[1],
                'played_at': row[2]
            }
            for row in results
        ]

    def get_player_recent_games(self, player_id: int, limit: int = 5) -> List[Dict]:
        """Hakee pelaajan viimeisimmät pelit"""
        sql = "SELECT score, game_mode, played_at FROM high_scores WHERE player_id = %s ORDER BY played_at DESC LIMIT %s"
        results = self._execute_query(sql, (player_id, limit))

        return [
            {
                'score': row[0],
                'game_mode': row[1],
                'played_at': row[2]
            }
            for row in results
        ]

    # LENTOKENTTÄ- JA MAATIEDOT

    def get_random_airport(self, exclude_ids: List[int] = None) -> Optional[Dict]:
        """Hakee satunnaisen lentokentän"""
        base_sql = """
                   SELECT a.id, \
                          a.ident, \
                          a.type, \
                          a.name, \
                          a.latitude_deg, \
                          a.longitude_deg,
                          a.elevation_ft, \
                          a.continent, \
                          a.iso_country, \
                          a.municipality, \
                          c.name as country_name
                   FROM airport a
                            LEFT JOIN country c ON a.iso_country = c.iso_country
                   WHERE a.type IN ('large_airport', 'medium_airport') \
                   """

        if exclude_ids:
            placeholders = ','.join(['%s'] * len(exclude_ids))
            sql = f"{base_sql} AND a.id NOT IN ({placeholders}) ORDER BY RAND() LIMIT 1"
            result = self._execute_query(sql, tuple(exclude_ids))
        else:
            sql = f"{base_sql} ORDER BY RAND() LIMIT 1"
            result = self._execute_query(sql)

        if result:
            row = result[0]
            return {
                'id': row[0], 'ident': row[1], 'type': row[2], 'name': row[3],
                'latitude_deg': row[4], 'longitude_deg': row[5], 'elevation_ft': row[6],
                'continent': row[7], 'iso_country': row[8], 'municipality': row[9],
                'country_name': row[10]
            }
        return None

    def get_random_country(self, exclude_codes: List[str] = None) -> Optional[Dict]:
        """Hakee satunnaisen maan"""
        base_sql = """
                   SELECT iso_country, name, continent, population, wikipedia_link, keywords
                   FROM country \
                   WHERE population IS NOT NULL \
                   """

        if exclude_codes:
            placeholders = ','.join(['%s'] * len(exclude_codes))
            sql = f"{base_sql} AND iso_country NOT IN ({placeholders}) ORDER BY RAND() LIMIT 1"
            result = self._execute_query(sql, tuple(exclude_codes))
        else:
            sql = f"{base_sql} ORDER BY RAND() LIMIT 1"
            result = self._execute_query(sql)

        if result:
            row = result[0]
            return {
                'iso_country': row[0], 'name': row[1], 'continent': row[2],
                'population': row[3], 'wikipedia_link': row[4], 'keywords': row[5]
            }
        return None


# ==============================
# PELILOGIIKKA
# ==============================

class GameEngine:
    """Pelin päälogiikka"""

    def __init__(self, db_manager):
        self.db = db_manager
        self.settings = GameSettings()
        self.state = GameState()
        self.used_ids = []
        self.used_country_codes = []

    def start_new_game(self, player_id: int, username: str, question_type: QuestionType,
                       game_mode: GameMode = GameMode.CLASSIC):
        """Aloittaa uuden pelin"""
        high_score = self.db.get_player_high_score(player_id, game_mode.value)

        self.state = GameState(
            game_mode=game_mode,
            player_id=player_id,
            player_username=username,
            high_score=high_score,
            question_type=question_type,
            lives=self._get_initial_lives(game_mode),
            time_remaining=self._get_initial_time(game_mode),
            start_time=time.time() if game_mode == GameMode.TIME_ATTACK else 0
        )

        self.used_ids = []
        self.used_country_codes = []
        self.state.current_item = self._get_next_item()
        self.state.next_item = self._get_next_item()

    def _get_initial_lives(self, game_mode: GameMode) -> int:
        """Palauttaa aloituselämät pelimuodon mukaan"""
        return self.settings.LIVES_CLASSIC if game_mode == GameMode.CLASSIC else self.settings.LIVES_OTHER

    def _get_initial_time(self, game_mode: GameMode) -> float:
        """Palauttaa aloitusajan pelimuodon mukaan"""
        return self.settings.TIME_ATTACK_DURATION if game_mode == GameMode.TIME_ATTACK else 0.0

    def _get_next_item(self) -> Optional[Dict]:
        """Hakee seuraavan kohteen kysymystyypistä riippuen"""
        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            item = self.db.get_random_airport(self.used_ids)
            if item:
                self.used_ids.append(item['id'])
        else:
            item = self.db.get_random_country(self.used_country_codes)
            if item:
                self.used_country_codes.append(item['iso_country'])
        return item

    def _get_value(self, item: Dict) -> float:
        """Palauttaa vertailtavan arvon kysymystyypistä riippuen"""
        if not item:
            return 0.0

        try:
            if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
                return float(item.get('elevation_ft', 0))
            else:
                return float(item.get('population', 0))
        except (ValueError, TypeError):
            return 0.0

    def update_time(self) -> bool:
        """Päivittää jäljellä olevan ajan time attack -tilassa"""
        if self.state.game_mode != GameMode.TIME_ATTACK or self.state.game_over:
            return False

        elapsed = time.time() - self.state.start_time
        self.state.time_remaining = max(0, self.settings.TIME_ATTACK_DURATION - elapsed)

        if self.state.time_remaining <= 0:
            self._end_game()
            return True
        return False

    def _end_game(self):
        """Päättää pelin ja tallentaa tuloksen"""
        self.state.game_over = True
        if self.state.player_id:
            self.db.save_score(self.state.player_id, self.state.score, self.state.game_mode.value)

    def make_guess(self, is_higher: bool) -> Tuple[bool, str]:
        """Käsittelee pelaajan arvauksen"""
        if self.state.game_over:
            return False, "Peli on päättynyt!"

        # Tarkista aika time attack -tilassa
        if self.state.game_mode == GameMode.TIME_ATTACK and self.update_time():
            return False, "Aika loppui!"

        current_value = self._get_value(self.state.current_item)
        next_value = self._get_value(self.state.next_item)
        correct = self._is_guess_correct(is_higher, current_value, next_value)

        # Näytä nykyinen arvo ensimmäisen arvauksen jälkeen
        if self.state.first_guess:
            self.state.first_guess = False
            self.state.show_current_value = True

        return self._handle_correct_guess() if correct else self._handle_incorrect_guess()

    def _is_guess_correct(self, is_higher: bool, current: float, next_val: float) -> bool:
        """Tarkistaa onko arvaus oikein"""
        return (is_higher and next_val >= current) or (not is_higher and next_val <= current)

    def _handle_correct_guess(self) -> Tuple[bool, str]:
        """Käsittelee oikean arvauksen"""
        self.state.score += 1
        message = f"Oikein! {self._format_item_name(self.state.next_item)}\n{self._format_value(self._get_value(self.state.next_item))}"

        # Tarkista uusi ennätys
        if self.state.score > self.state.high_score:
            self.state.high_score = self.state.score
            message += "\n🎉 UUSI ENNÄTYS! 🎉"

        # Siirry seuraavaan kohteeseen
        self.state.current_item = self.state.next_item
        self.state.next_item = self._get_next_item()

        if self.state.score % 10 == 0:
            message += f"\n\nHienoa! {self.state.score} pistettä!"

        return True, message

    def _handle_incorrect_guess(self) -> Tuple[bool, str]:
        """Käsittelee väärän arvauksen"""
        self.state.lives -= 1
        message = f"Väärin! {self._format_item_name(self.state.next_item)}\n{self._format_value(self._get_value(self.state.next_item))}"

        if self.state.lives <= 0:
            self._end_game()
            message += self._get_game_over_message()
        else:
            # Pysy nykyisessä kohteessa, hae uusi vertailukohde
            self.state.next_item = self._get_next_item()

        return False, message

    def _get_game_over_message(self) -> str:
        """Palauttaa pelin päättymisviestin"""
        messages = {
            GameMode.CLASSIC: "",
            GameMode.SUDDEN_DEATH: "Äkkikuolema-tila: Yksi virhe riitti!\n",
            GameMode.TIME_ATTACK: f"Aikaa jäljellä: {self.state.time_remaining:.1f}s\n"
        }

        return (f"\n\n{'=' * 50}\nPELI PÄÄTTYI!\n"
                f"Pistemäärä: {self.state.score}\n"
                f"{messages[self.state.game_mode]}"
                f"Ennätyksesi: {self.state.high_score}\n"
                f"{'=' * 50}")

    def _format_item_name(self, item: Dict) -> str:
        """Muotoilee kohteen nimen näyttämistä varten"""
        if not item:
            return "Tuntematon"

        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            name = item.get('name', 'Tuntematon')
            country = item.get('country_name', '')
            municipality = item.get('municipality', '')

            if municipality and country:
                return f"{name} ({municipality}, {country})"
            elif country:
                return f"{name} ({country})"
            return name
        else:
            return item.get('name', 'Tuntematon')

    def _format_value(self, value: float) -> str:
        """Muotoilee arvon näyttämistä varten"""
        value_type = "Korkeus" if self.state.question_type == QuestionType.AIRPORT_ELEVATION else "Väkiluku"
        unit = " ft" if self.state.question_type == QuestionType.AIRPORT_ELEVATION else ""
        return f"{value_type}: {int(value):,}{unit}".replace(',', ' ')

    def get_current_display(self) -> Dict:
        """Palauttaa näytettävät tiedot"""
        # Päivitä aika time attack -tilassa
        if self.state.game_mode == GameMode.TIME_ATTACK:
            self.update_time()

        current_value = int(self._get_value(self.state.current_item))

        return {
            'score': self.state.score,
            'lives': self.state.lives,
            'current_item': self._format_item_name(self.state.current_item),
            'current_value': current_value,
            'current_value_formatted': self._format_value(current_value),
            'next_item': self._format_item_name(self.state.next_item),
            'question_type': "Lentokentän korkeus" if self.state.question_type == QuestionType.AIRPORT_ELEVATION else "Maan väkiluku",
            'game_over': self.state.game_over,
            'high_score': self.state.high_score,
            'player_username': self.state.player_username,
            'show_current_value': self.state.show_current_value,
            'first_guess': self.state.first_guess,
            'game_mode': self.state.game_mode,
            'time_remaining': self.state.time_remaining
        }



# KÄYTTÖLIITTYMÄKOMPONENTIT

class MenuRenderer:
    """Valikoiden renderöinti"""

    @staticmethod
    def show_main_menu() -> str:
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

    @staticmethod
    def show_game_mode_menu() -> str:
        """Näyttää pelimuodon valikon"""
        print("\n" + "=" * 60)
        print(" VALITSE PELIMUOTO ")
        print("=" * 60)
        print("1. Klassinen - 3 elämää, rauhallinen tempo")
        print("2. Äkkikuolema - 1 elämä, jännittävä")
        print("3. Aikaraja - 1 elämä, 60 sekuntia, nopeatempoinen")
        print("4. Takaisin päävalikkoon")

        while True:
            choice = input("\nValitse (1-4): ")
            if choice in ['1', '2', '3', '4']:
                return choice
            print("Virheellinen valinta! Valitse 1, 2, 3 tai 4.")

    @staticmethod
    def show_question_type_menu() -> str:
        """Näyttää kysymystyypin valikon"""
        print("\n" + "=" * 60)
        print(" VALITSE KYSYMYSTYYPPI ")
        print("=" * 60)
        print("1. Lentokenttien korkeudet")
        print("2. Maiden väkiluvut")
        print("3. Takaisin päävalikkoon")

        while True:
            choice = input("\nValitse (1-3): ")
            if choice in ['1', '2', '3']:
                return choice
            print("Virheellinen valinta! Valitse 1, 2 tai 3.")

    @staticmethod
    def show_leaderboard_mode_menu() -> str:
        """Näyttää pistetaulukon valikon"""
        print("\nValitse pistetaulukon pelimuoto:")
        print("1. Klassinen")
        print("2. Äkkikuolema")
        print("3. Aikaraja")
        return input("\nValitse (1-3) tai Enter palataksesi: ")


class GameDisplay:
    """Pelinäkymän renderöinti"""

    @staticmethod
    def show_game_header(display_info: dict):
        """Näyttää pelin otsikon"""
        mode_descriptions = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        mode_name = mode_descriptions.get(display_info['game_mode'].value, 'Tuntematon')

        lives_display = '❤️ ' * display_info['lives'] if display_info['game_mode'].value == 'classic' else '💀' if \
        display_info['game_mode'].value == 'sudden_death' else '⏰'
        time_display = f" | Aikaa: {display_info['time_remaining']:.1f}s" if display_info[
                                                                                 'game_mode'].value == 'time_attack' else ""

        print("\n" + "-" * 60)
        print(f"Pelaaja: {display_info['player_username']} | "
              f"Pisteet: {display_info['score']} | "
              f"Ennätys: {display_info['high_score']} | "
              f"Elämät: {lives_display} ({mode_name}){time_display}")
        print(f"Kysymystyyppi: {display_info['question_type']}")
        print("-" * 60)

    @staticmethod
    def show_game_content(display_info: dict, question_type: QuestionType):
        """Näyttää pelin sisällön"""
        current_label = "Korkeus" if question_type == QuestionType.AIRPORT_ELEVATION else "Väkiluku"

        print(f"\nNykyinen: {display_info['current_item']}")

        if display_info['show_current_value']:
            print(f"{display_info['current_value_formatted']}")
        else:
            print(f"{current_label}: ???")

        print(f"\nSeuraava: {display_info['next_item']}")
        print(f"{current_label}: ???")


class StatisticsRenderer:
    """Tilastojen renderöinti"""

    @staticmethod
    def show_player_statistics(db: DatabaseManager, player_id: int, username: str):
        """Näyttää pelaajan tilastot"""
        print("\n" + "=" * 60)
        print(f" TILASTOT - {username} ")
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
                mode_name = StatisticsRenderer._get_mode_name(game['game_mode'])
                date_str = game['played_at'].strftime('%d.%m.%Y %H:%M')
                print(f"{game['score']:4} pistettä  ({mode_name})  ({date_str})")
        else:
            print("Ei vielä pelattuja pelejä!")

        input("\nPaina Enter palataksesi...")

    @staticmethod
    def _get_mode_name(game_mode: str) -> str:
        """Palauttaa pelimuodon nimen"""
        mode_names = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        return mode_names.get(game_mode, game_mode)

    @staticmethod
    def show_leaderboard(db: DatabaseManager, game_mode: str = 'classic'):
        """Näyttää pistetaulukon"""
        mode_names = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        mode_name = mode_names.get(game_mode, game_mode)

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



# PÄÄOHJELMA


class HigherOrLowerGame:
    """Pääsovellus"""

    def __init__(self):
        self.db = DatabaseManager()
        self.game = GameEngine(self.db)
        self.player_id = None
        self.username = None

    def run(self):
        """Käynnistää sovelluksen"""
        self._show_welcome_message()

        if not self.db.connect():
            print("\nVirhe: Tietokantayhteys epäonnistui!")
            return

        if not self._login_or_register():
            self.db.close()
            return

        self._main_loop()

    def _show_welcome_message(self):
        """Näyttää tervetulosanoman"""
        print("=" * 60)
        print(" HIGHER OR LOWER - Lentokentät ja maat ")
        print("=" * 60)
        print("\nYhdistetään tietokantaan...")

    def _login_or_register(self) -> bool:
        """Käsittelee kirjautumisen/rekisteröitymisen"""
        print("\n" + "=" * 60)
        print(" KIRJAUTUMINEN ")
        print("=" * 60)

        while True:
            username = input("\nAnna käyttäjänimesi (tai 'q' lopettaaksesi): ").strip()

            if username.lower() == 'q':
                return False

            if not username:
                print("Käyttäjänimi ei voi olla tyhjä!")
                continue

            if len(username) < 3:
                print("Käyttäjänimen pitää olla vähintään 3 merkkiä!")
                continue

            player_id = self.db.get_or_create_player(username)
            if player_id:
                player = self.db.get_player_by_username(username)
                if player:
                    self.player_id = player_id
                    self.username = username
                    print(f"\nTervetuloa takaisin, {username}!")
                    return True
            else:
                print("Virhe käyttäjän luonnissa. Yritä toista nimeä.")

    def _main_loop(self):
        """Pääsovelluksen silmukka"""
        while True:
            choice = MenuRenderer.show_main_menu()

            if choice == '1':
                self._handle_play_option()
            elif choice == '2':
                StatisticsRenderer.show_player_statistics(self.db, self.player_id, self.username)
            elif choice == '3':
                self._handle_leaderboard_option()
            elif choice == '4':
                if not self._login_or_register():
                    break
            elif choice == '5':
                print("\nKiitos pelaamisesta! Näkemiin!")
                break
            else:
                print("Virheellinen valinta!")

        self.db.close()

    def _handle_play_option(self):
        """Käsittelee pelin aloituksen"""
        game_mode = self._select_game_mode()
        if not game_mode:
            return

        question_type = self._select_question_type()
        if not question_type:
            return

        self._play_game(game_mode, question_type)

    def _select_game_mode(self) -> Optional[GameMode]:
        """Käsittelee pelimuodon valinnan"""
        while True:
            choice = MenuRenderer.show_game_mode_menu()

            if choice == '1':
                return GameMode.CLASSIC
            elif choice == '2':
                return GameMode.SUDDEN_DEATH
            elif choice == '3':
                return GameMode.TIME_ATTACK
            elif choice == '4':
                return None

    def _select_question_type(self) -> Optional[QuestionType]:
        """Käsittelee kysymystyypin valinnan"""
        while True:
            choice = MenuRenderer.show_question_type_menu()

            if choice == '1':
                return QuestionType.AIRPORT_ELEVATION
            elif choice == '2':
                return QuestionType.COUNTRY_POPULATION
            elif choice == '3':
                return None

    def _play_game(self, game_mode: GameMode, question_type: QuestionType):
        """Suorittaa pelin"""
        self._show_game_intro(game_mode, question_type)
        input("Paina Enter aloittaaksesi...")

        self.game.start_new_game(self.player_id, self.username, question_type, game_mode)

        if not self._validate_game_start():
            return

        self._run_game_loop(question_type)

    def _show_game_intro(self, game_mode: GameMode, question_type: QuestionType):
        """Näyttää pelin aloitusotsikon"""
        title = "LENTOKENTTIEN KORKEUDET" if question_type == QuestionType.AIRPORT_ELEVATION else "MAIDEN VÄKILUVUT"

        print("\n" + "=" * 60)
        print(f" {title} ")
        print("=" * 60)

        intro_texts = {
            GameMode.CLASSIC: "Klassinen tila - 3 elämää\nArvaa, onko seuraava arvo HIGHER vai LOWER!",
            GameMode.SUDDEN_DEATH: "ÄKKIKUOLEMA - 1 elämä!\nYksi virhe päättää pelin!",
            GameMode.TIME_ATTACK: "AIKARAJA - 60 sekuntia!\n1 elämä, 60 sekuntia aikaa!"
        }

        print(intro_texts.get(game_mode, ""))
        print("Onnea matkaan!\n")

    def _validate_game_start(self) -> bool:
        """Varmistaa että peli voi alkaa"""
        if not self.game.state.current_item or not self.game.state.next_item:
            print("\nVirhe: Ei voitu hakea tietoja!")
            return False
        return True

    def _run_game_loop(self, question_type: QuestionType):
        """Suorittaa pelisilmukan"""
        while not self.game.state.game_over:
            display_info = self.game.get_current_display()

            GameDisplay.show_game_header(display_info)
            GameDisplay.show_game_content(display_info, question_type)

            player_choice = self._get_player_input()
            if not player_choice:
                break

            self._process_player_guess(player_choice)

        self._handle_game_end()

    def _get_player_input(self) -> str:
        """Hakee pelaajan syötteen"""
        while True:
            choice = input("\nOnko seuraava HIGHER vai LOWER? (h/l) tai (q lopettaaksesi): ").lower()
            if choice in ['h', 'l', 'q']:
                return choice
            print("Virheellinen valinta!")

    def _process_player_guess(self, choice: str):
        """Käsittelee pelaajan arvauksen"""
        if choice == 'q':
            print("\nLopetetaan peli...")
            return

        is_higher = choice == 'h'
        correct, message = self.game.make_guess(is_higher)

        print(f"\n{'✓' if correct else '✗'} {message}")

        # Käsittele ajan loppuminen time attack -tilassa
        if (self.game.state.game_over and
                self.game.state.game_mode == GameMode.TIME_ATTACK and
                self.game.state.time_remaining <= 0):
            print(f"\n⏰ AIKA LOPPUI! Saavutit {self.game.state.score} pistettä!")
            return

        if not correct and not self.game.state.game_over:
            input("\nPaina Enter jatkaaksesi...")

    def _handle_game_end(self):
        """Käsittelee pelin päättymisen"""
        if (self.game.state.game_over and
                self.game.state.game_mode != GameMode.TIME_ATTACK):
            input("\nPaina Enter palataksesi valikkoon...")

    def _handle_leaderboard_option(self):
        """Käsittelee pistetaulukon näyttämisen"""
        choice = MenuRenderer.show_leaderboard_mode_menu()

        if choice == '1':
            StatisticsRenderer.show_leaderboard(self.db, 'classic')
        elif choice == '2':
            StatisticsRenderer.show_leaderboard(self.db, 'sudden_death')
        elif choice == '3':
            StatisticsRenderer.show_leaderboard(self.db, 'time_attack')


def main():
    """Pääohjelma"""
    try:
        game = HigherOrLowerGame()
        game.run()
    except KeyboardInterrupt:
        print("\n\nPeli keskeytetty. Näkemiin!")
    except Exception as e:
        print(f"\nOdottamaton virhe: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()