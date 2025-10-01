# database.py - MySQL-tietokantayhteydet ja kyselyt
import mysql.connector
from typing import List, Dict, Optional


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
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import random


class QuestionType(Enum):
    """Kysymystyypit"""
    AIRPORT_ELEVATION = "elevation"
    # Voit lisätä myöhemmin:
    # AIRPORT_PASSENGERS = "passengers"
    # COUNTRY_POPULATION = "population"
    # COUNTRY_AREA = "area"


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


class GameEngine:
    """Pelin päälogiikka"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.state = GameState()
        self.used_ids = []

    def start_new_game(self, game_mode: GameMode = GameMode.CLASSIC):
        """Aloittaa uuden pelin"""
        self.state = GameState(game_mode=game_mode)
        self.used_ids = []
        self.state.question_type = self._select_question_type()
        self.state.current_item = self._get_next_item()
        self.state.next_item = self._get_next_item()

    def _select_question_type(self) -> QuestionType:
        """Valitsee satunnaisen kysymystyypin"""
        # Tällä hetkellä vain lentokenttien korkeus
        return QuestionType.AIRPORT_ELEVATION

    def _get_next_item(self) -> Optional[Dict]:
        """Hakee seuraavan kohteen kysymystyypistä riippuen"""
        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            item = self.db.get_random_airport(self.used_ids)
            if item:
                self.used_ids.append(item['id'])
            return item
        else:
            # Maiden kysymykset tulossa
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
        """
        Käsittelee pelaajan arvauksen
        Returns: (oikein/väärin, viesti)
        """
        if self.state.game_over:
            return False, "Peli on päättynyt!"

        current_value = self._get_value(self.state.current_item)
        next_value = self._get_value(self.state.next_item)

        # Tarkista arvaus
        correct = (is_higher and next_value >= current_value) or \
                  (not is_higher and next_value <= current_value)

        if correct:
            self.state.score += 1
            message = f"Oikein! {self._format_item_name(self.state.next_item)}\nKorkeus: {int(next_value)} ft"

            # Siirry seuraavaan
            self.state.current_item = self.state.next_item
            self.state.next_item = self._get_next_item()

            # Vaihda kysymystyyppiä joka 10. pisteen kohdalla (tulevaisuudessa)
            if self.state.score % 10 == 0:
                self.state.question_type = self._select_question_type()
                message += f"\n\nHienoa! Jatketaan samalla kysymystyypillä: {self._get_question_description()}"
        else:
            self.state.lives -= 1
            message = f"Väärin! {self._format_item_name(self.state.next_item)}\nKorkeus: {int(next_value)} ft"

            if self.state.lives <= 0:
                self.state.game_over = True
                if self.state.score > self.state.high_score:
                    self.state.high_score = self.state.score
                message += f"\n\n{'=' * 50}\nPELI PÄÄTTYI!\nLopullinen pistemäärä: {self.state.score}\n{'=' * 50}"

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
            'high_score': self.state.high_score
        }


# main.py - Pääohjelma (konsoli-versio)
def main():
    """Pääohjelma - yksinkertainen konsoli-versio"""

    print("=" * 60)
    print("HIGHER OR LOWER - Lentokentät ja maat")
    print("=" * 60)
    print("\nYhdistetään tietokantaan...")

    # Alusta tietokanta
    db = DatabaseManager(
        host="127.0.0.1",
        user="pythonUser",
        password="salasana",
        database="flight_game"
    )

    if not db.connect():
        print("\nVirhe: Tietokantayhteys epäonnistui!")
        print("Tarkista että MySQL-palvelin on käynnissä ja tiedot ovat oikein.")
        return

    # Luo pelimoottori
    game = GameEngine(db)

    print("\nArvaa, onko seuraava arvo HIGHER (suurempi) vai LOWER (pienempi)!")
    print("Sinulla on 3 elämää. Onnea matkaan!\n")

    # Aloita peli
    game.start_new_game()

    if not game.state.current_item or not game.state.next_item:
        print("\nVirhe: Ei voitu hakea lentokenttätietoja!")
        db.close()
        return

    while not game.state.game_over:
        display = game.get_current_display()

        print("\n" + "-" * 60)
        print(f"Pisteet: {display['score']} | Elämät: {'❤️ ' * display['lives']}")
        print(f"Kysymystyyppi: {display['question_type']}")
        print("-" * 60)
        print(f"\nNykyinen: {display['current_item']}")
        print(f"Korkeus: {display['current_value']} ft")
        print(f"\nSeuraava: {display['next_item']}")
        print(f"Korkeus: ???")

        # Kysy pelaajalta
        while True:
            choice = input("\nOnko seuraava HIGHER vai LOWER? (h/l) tai (q lopettaaksesi): ").lower()
            if choice in ['h', 'l', 'q']:
                break
            print("Virheellinen valinta! Syötä 'h' (higher), 'l' (lower) tai 'q' (quit)")

        if choice == 'q':
            print("\nLopetetaan peli...")
            break

        is_higher = choice == 'h'
        correct, message = game.make_guess(is_higher)

        print(f"\n{'✓' if correct else '✗'} {message}")

        if not correct and not game.state.game_over:
            input("\nPaina Enter jatkaaksesi...")

    if game.state.game_over:
        print("\n" + "=" * 60)
        print(f"PELI PÄÄTTYI!")
        print(f"Lopullinen pistemäärä: {game.state.score}")
        if game.state.high_score > 0:
            print(f"Parhain tulos tässä istunnossa: {game.state.high_score}")
        print("=" * 60)

    db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPeli keskeytetty. Näkemiin!")
    except Exception as e:
        print(f"\nVirhe: {e}")