import mysql.connector
import time
from enum import Enum




# PELIN ASETUKSET JA TILA


class QuestionType(Enum):

    AIRPORT_ELEVATION = "elevation"
    COUNTRY_POPULATION = "population"


class GameMode(Enum):

    CLASSIC = "classic"
    SUDDEN_DEATH = "sudden_death"
    TIME_ATTACK = "time_attack"


class GameSettings:


    def __init__(self):
        self.LIVES_CLASSIC = 3
        self.LIVES_OTHER = 1
        self.TIME_ATTACK_DURATION = 60.0


class GameState:

    def __init__(self):
        self.score = 0
        self.lives = 3
        self.current_item = None
        self.next_item = None
        self.question_type = None
        self.game_over = False
        self.high_score = 0
        self.game_mode = GameMode.CLASSIC
        self.player_id = None
        self.player_username = ""
        self.show_current_value = False
        self.first_guess = True
        self.time_remaining = 0
        self.start_time = 0



# TIETOKANTA


class DatabaseManager:

    def __init__(self, host="127.0.0.1", user="pythonUser", password="salasana", database="flight_game"):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None

    def connect(self):

        try:
            self.connection = mysql.connector.connect(**self.config)
            return True
        except mysql.connector.Error:
            return False

    def close(self):

        if self.connection and self.connection.is_connected():
            self.connection.close()

    def suorita_kysely(self, query, params=None):

        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except mysql.connector.Error as err:
            return []
        finally:
            cursor.close()

    def suorita_paivitys(self, query, params=None):

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.connection.commit()
            return True
        finally:
            cursor.close()

    # KÄYTTÄJÄHALLINTA

    def luo_pelaaja(self, username):

        try:
            sql = "INSERT INTO players (username) VALUES (%s)"
            if self.suorita_paivitys(sql, (username,)):
                cursor = self.connection.cursor()
                cursor.execute("SELECT LAST_INSERT_ID()")
                return cursor.fetchone()[0]
            return None
        except mysql.connector.IntegrityError:
            print(f"Käyttäjänimi '{username}' on jo olemassa!")
            return None

    def etsi_pelaaja_kayttajanimella(self, username):

        sql = "SELECT id, username, created_at FROM players WHERE username = %s"
        result = self.suorita_kysely(sql, (username,))

        if result:
            return {
                'id': result[0][0],
                'username': result[0][1],
                'created_at': result[0][2]
            }
        return None

    def etsi_tai_luo_pelaaja(self, username):

        player = self.etsi_pelaaja_kayttajanimella(username)
        if player:
            return player['id']
        else:
            return self.luo_pelaaja(username)

    # HIGH SCORE -HALLINTA

    def tallenna_score(self, player_id, score, game_mode='classic'):

        sql = "INSERT INTO high_scores (player_id, score, game_mode) VALUES (%s, %s, %s)"
        return self.suorita_paivitys(sql, (player_id, score, game_mode))

    def etsi_pelaajan_highscore(self, player_id, game_mode='classic'):

        sql = "SELECT MAX(score) FROM high_scores WHERE player_id = %s AND game_mode = %s"
        result = self.suorita_kysely(sql, (player_id, game_mode))
        if result and result[0][0] is not None:
            return result[0][0]
        return 0

    def etsi_pelaajan_tilastot(self, player_id):

        sql = """
              SELECT COUNT(*)   as games_played, \
                     MAX(score) as best_score,
                     AVG(score) as avg_score, \
                     MIN(score) as worst_score
              FROM high_scores \
              WHERE player_id = %s \
              """
        result = self.suorita_kysely(sql, (player_id,))

        if result and result[0]:
            avg_score = result[0][2]
            if avg_score is not None:
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0

            return {
                'games_played': result[0][0] or 0,
                'best_score': result[0][1] or 0,
                'avg_score': avg_score,
                'worst_score': result[0][3] or 0
            }
        return {'games_played': 0, 'best_score': 0, 'avg_score': 0, 'worst_score': 0}

    def etsi_top_scoret(self, limit=10, game_mode='classic'):

        sql = """
              SELECT p.username, h.score, h.played_at
              FROM high_scores h
                       JOIN players p ON h.player_id = p.id
              WHERE h.game_mode = %s
              ORDER BY h.score DESC
                  LIMIT %s \
              """
        results = self.suorita_kysely(sql, (game_mode, limit))

        scores = []
        for row in results:
            scores.append({
                'username': row[0],
                'score': row[1],
                'played_at': row[2]
            })
        return scores

    def get_player_recent_games(self, player_id, limit=5):

        sql = "SELECT score, game_mode, played_at FROM high_scores WHERE player_id = %s ORDER BY played_at DESC LIMIT %s"
        results = self.suorita_kysely(sql, (player_id, limit))

        games = []
        for row in results:
            games.append({
                'score': row[0],
                'game_mode': row[1],
                'played_at': row[2]
            })
        return games

    # LENTOKENTTÄ- JA MAATIEDOT

    def etsi_random_lentokentta(self, exclude_ids=None):

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

        if exclude_ids and len(exclude_ids) > 0:
            placeholders = ','.join(['%s'] * len(exclude_ids))
            sql = f"{base_sql} AND a.id NOT IN ({placeholders}) ORDER BY RAND() LIMIT 1"
            result = self.suorita_kysely(sql, tuple(exclude_ids))
        else:
            sql = f"{base_sql} ORDER BY RAND() LIMIT 1"
            result = self.suorita_kysely(sql)

        if result:
            row = result[0]
            return {
                'id': row[0], 'ident': row[1], 'type': row[2], 'name': row[3],
                'latitude_deg': row[4], 'longitude_deg': row[5], 'elevation_ft': row[6],
                'continent': row[7], 'iso_country': row[8], 'municipality': row[9],
                'country_name': row[10]
            }
        return None

    def etsi_random_maa(self, exclude_codes=None):

        base_sql = """
                   SELECT iso_country, name, continent, population, wikipedia_link, keywords
                   FROM country \
                   WHERE population IS NOT NULL \
                   """

        if exclude_codes and len(exclude_codes) > 0:
            placeholders = ','.join(['%s'] * len(exclude_codes))
            sql = f"{base_sql} AND iso_country NOT IN ({placeholders}) ORDER BY RAND() LIMIT 1"
            result = self.suorita_kysely(sql, tuple(exclude_codes))
        else:
            sql = f"{base_sql} ORDER BY RAND() LIMIT 1"
            result = self.suorita_kysely(sql)

        if result:
            row = result[0]
            return {
                'iso_country': row[0], 'name': row[1], 'continent': row[2],
                'population': row[3], 'wikipedia_link': row[4], 'keywords': row[5]
            }
        return None



# PELILOGIIKKA


class GameEngine:


    def __init__(self, db_manager):
        self.db = db_manager
        self.settings = GameSettings()
        self.state = GameState()
        self.used_ids = []
        self.used_country_codes = []

    def aloita_uusi_peli(self, player_id, username, question_type, game_mode=GameMode.CLASSIC):

        high_score = self.db.etsi_pelaajan_highscore(player_id, game_mode.value)

        self.state = GameState()
        self.state.game_mode = game_mode
        self.state.player_id = player_id
        self.state.player_username = username
        self.state.high_score = high_score
        self.state.question_type = question_type
        self.state.lives = self.get_initial_lives(game_mode)
        self.state.time_remaining = self.get_initial_time(game_mode)
        self.state.start_time = time.time() if game_mode == GameMode.TIME_ATTACK else 0

        self.used_ids = []
        self.used_country_codes = []
        self.state.current_item = self.get_next_item()
        self.state.next_item = self.get_next_item()

    def get_initial_lives(self, game_mode):

        if game_mode == GameMode.CLASSIC:
            return self.settings.LIVES_CLASSIC
        return self.settings.LIVES_OTHER

    def get_initial_time(self, game_mode):

        if game_mode == GameMode.TIME_ATTACK:
            return self.settings.TIME_ATTACK_DURATION
        return 0.0

    def get_next_item(self):

        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            item = self.db.etsi_random_lentokentta(self.used_ids)
            if item:
                self.used_ids.append(item['id'])
        else:
            item = self.db.etsi_random_maa(self.used_country_codes)
            if item:
                self.used_country_codes.append(item['iso_country'])
        return item

    def get_value(self, item):

        if not item:
            return 0.0

        try:
            if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
                return float(item.get('elevation_ft', 0))
            else:
                return float(item.get('population', 0))
        except (ValueError, TypeError):
            return 0.0

    def paivita_aika(self):

        if self.state.game_mode != GameMode.TIME_ATTACK or self.state.game_over:
            return False

        elapsed = time.time() - self.state.start_time
        self.state.time_remaining = max(0, self.settings.TIME_ATTACK_DURATION - elapsed)

        if self.state.time_remaining <= 0:
            self.lopeta_peli()
            return True
        return False

    def lopeta_peli(self):

        self.state.game_over = True
        if self.state.player_id:
            self.db.tallenna_score(self.state.player_id, self.state.score, self.state.game_mode.value)

    def arvaus(self, is_higher):

        if self.state.game_over:
            return False, "Peli on päättynyt!"


        if self.state.game_mode == GameMode.TIME_ATTACK and self.paivita_aika():
            return False, "Aika loppui!"

        current_value = self.get_value(self.state.current_item)
        next_value = self.get_value(self.state.next_item)
        correct = self.is_guess_correct(is_higher, current_value, next_value)


        if self.state.first_guess:
            self.state.first_guess = False
            self.state.show_current_value = True

        if correct:
            return self.handle_correct_guess()
        else:
            return self.handle_incorrect_guess()

    def is_guess_correct(self, is_higher, current, next_val):

        if is_higher:
            return next_val >= current
        else:
            return next_val <= current

    def handle_correct_guess(self):

        self.state.score += 1
        message = f"Oikein! {self.format_item_name(self.state.next_item)}\n{self.format_value(self.get_value(self.state.next_item))}"


        if self.state.score > self.state.high_score:
            self.state.high_score = self.state.score
            message += "\n UUSI ENNÄTYS! "


        self.state.current_item = self.state.next_item
        self.state.next_item = self.get_next_item()

        if self.state.score % 10 == 0:
            message += f"\n\nHienoa! {self.state.score} pistettä!"

        return True, message

    def handle_incorrect_guess(self):

        self.state.lives -= 1
        message = f"Väärin! {self.format_item_name(self.state.next_item)}\n{self.format_value(self.get_value(self.state.next_item))}"

        if self.state.lives <= 0:
            self.lopeta_peli()
            message += self.get_game_over_message()
        else:

            self.state.next_item = self.get_next_item()

        return False, message

    def get_game_over_message(self):

        message = f"\n\n{'=' * 50}\nPELI PÄÄTTYI!\nPistemäärä: {self.state.score}\n"

        if self.state.game_mode == GameMode.SUDDEN_DEATH:
            message += "Äkkikuolema-tila: Yksi virhe riitti!\n"
        elif self.state.game_mode == GameMode.TIME_ATTACK:
            message += f"Aikaa jäljellä: {self.state.time_remaining:.1f}s\n"

        message += f"Ennätyksesi: {self.state.high_score}\n{'=' * 50}"
        return message

    def format_item_name(self, item):

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

    def format_value(self, value):

        if self.state.question_type == QuestionType.AIRPORT_ELEVATION:
            return f"Korkeus: {int(value):,} ft".replace(',', ' ')
        else:
            return f"Väkiluku: {int(value):,}".replace(',', ' ')

    def get_current_display(self):

        if self.state.game_mode == GameMode.TIME_ATTACK:
            self.paivita_aika()

        current_value = int(self.get_value(self.state.current_item))

        return {
            'score': self.state.score,
            'lives': self.state.lives,
            'current_item': self.format_item_name(self.state.current_item),
            'current_value': current_value,
            'current_value_formatted': self.format_value(current_value),
            'next_item': self.format_item_name(self.state.next_item),
            'question_type': "Lentokentän korkeus" if self.state.question_type == QuestionType.AIRPORT_ELEVATION else "Maan väkiluku",
            'game_over': self.state.game_over,
            'high_score': self.state.high_score,
            'player_username': self.state.player_username,
            'show_current_value': self.state.show_current_value,
            'first_guess': self.state.first_guess,
            'game_mode': self.state.game_mode,
            'time_remaining': self.state.time_remaining
        }



# KÄYTTÖLIITTYMÄ


class MenuRenderer:


    def __init__(self):
        pass

    def nayta_paavalikko(self):

        print("\n" + "=" * 60)
        print(" PÄÄVALIKKO ")
        print("=" * 60)
        print("1. Pelaa")
        print("2. Omat tilastot")
        print("3. Pistetaulukko (Top 10)")
        print("4. Vaihda käyttäjää")
        print("5. Lopeta")
        return input("\nValitse (1-5): ")

    def nayta_pelimoodi_valikko(self):

        print("\n" + "=" * 60)
        print(" VALITSE PELIMUOTO ")
        print("=" * 60)
        print("1. Klassinen - 3 elämää")
        print("2. Äkkikuolema - 1 elämä, yksi virhe päättää pelin")
        print("3. Aikaraja - 1 elämä, 60 sekuntia, nopeatempoinen")
        print("4. Takaisin päävalikkoon")

        while True:
            choice = input("\nValitse (1-4): ")
            if choice in ['1', '2', '3', '4']:
                return choice
            print("Virheellinen valinta! Valitse 1, 2, 3 tai 4.")

    def nayta_kysymystyyppivalikko(self):

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

    def nayta_pistetaulukko_pelimoodi(self):

        print("\nValitse pistetaulukon pelimuoto:")
        print("1. Klassinen")
        print("2. Äkkikuolema")
        print("3. Aikaraja")
        return input("\nValitse (1-3) tai Enter palataksesi: ")


class GameDisplay:


    def __init__(self):
        pass

    def show_game_header(self, display_info):

        mode_descriptions = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        mode_name = mode_descriptions.get(display_info['game_mode'].value, 'Tuntematon')

        if display_info['game_mode'].value == 'classic':
            lives_display = '❤️ ' * display_info['lives']
        elif display_info['game_mode'].value == 'sudden_death':
            lives_display = '💀'
        else:
            lives_display = '⏰'

        time_display = f" | Aikaa: {display_info['time_remaining']:.1f}s" if display_info[
                                                                                 'game_mode'].value == 'time_attack' else ""

        print("\n" + "-" * 60)
        print(f"Pelaaja: {display_info['player_username']} | "
              f"Pisteet: {display_info['score']} | "
              f"Ennätys: {display_info['high_score']} | "
              f"Elämät: {lives_display} ({mode_name}){time_display}")
        print(f"Kysymystyyppi: {display_info['question_type']}")
        print("-" * 60)

    def show_game_content(self, display_info, question_type):

        if question_type == QuestionType.AIRPORT_ELEVATION:
            current_label = "Korkeus"
        else:
            current_label = "Väkiluku"

        print(f"\nNykyinen: {display_info['current_item']}")

        if display_info['show_current_value']:
            print(f"{display_info['current_value_formatted']}")
        else:
            print(f"{current_label}: ???")

        print(f"\nSeuraava: {display_info['next_item']}")
        print(f"{current_label}: ???")


class StatisticsRenderer:


    def __init__(self):
        pass

    def nayta_pelaajan_tilastot(self, db, player_id, username):

        print("\n" + "=" * 60)
        print(f" TILASTOT - {username} ")
        print("=" * 60)

        stats = db.etsi_pelaajan_tilastot(player_id)

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
                mode_name = self._get_mode_name(game['game_mode'])
                date_str = game['played_at'].strftime('%d.%m.%Y %H:%M')
                print(f"{game['score']:4} pistettä  ({mode_name})  ({date_str})")
        else:
            print("Ei vielä pelattuja pelejä!")

        input("\nPaina Enter palataksesi...")

    def _get_mode_name(self, game_mode):

        mode_names = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        return mode_names.get(game_mode, game_mode)

    def nayta_pistetaulukko(self, db, game_mode='classic'):

        mode_names = {
            'classic': 'Klassinen',
            'sudden_death': 'Äkkikuolema',
            'time_attack': 'Aikaraja'
        }
        mode_name = mode_names.get(game_mode, game_mode)

        print("\n" + "=" * 60)
        print(f" PISTETAULUKKO - TOP 10 ({mode_name}) ")
        print("=" * 60)

        top_scores = db.etsi_top_scoret(10, game_mode)

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
        self.menu_renderer = MenuRenderer()
        self.game_display = GameDisplay()
        self.statistics_renderer = StatisticsRenderer()
        self.player_id = None
        self.username = None
        self.quit_requested = False

    def run(self):


        if not self.db.connect():
            return

        if not self._login_or_register():
            self.db.close()
            return

        self._main_loop()


    def _login_or_register(self):

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

            player_id = self.db.etsi_tai_luo_pelaaja(username)
            if player_id:
                player = self.db.etsi_pelaaja_kayttajanimella(username)
                if player:
                    self.player_id = player_id
                    self.username = username
                    print(f"\nTervetuloa takaisin, {username}!")
                    return True
            else:
                print("Virhe käyttäjän luonnissa. Yritä toista nimeä.")

    def _main_loop(self):

        while True:
            choice = self.menu_renderer.nayta_paavalikko()

            if choice == '1':
                self.handle_play_option()
                if self.quit_requested:
                    self.quit_requested = False
                    continue
            elif choice == '2':
                self.statistics_renderer.nayta_pelaajan_tilastot(self.db, self.player_id, self.username)
            elif choice == '3':
                self.handle_leaderboard_option()
            elif choice == '4':
                if not self._login_or_register():
                    break
            elif choice == '5':
                print("\nKiitos pelaamisesta! Näkemiin!")
                break
            else:
                print("Virheellinen valinta!")

        self.db.close()

    def handle_play_option(self):

        game_mode = self.valitse_pelimoodi()
        if not game_mode:
            return

        question_type = self.valitse_kysymystyyppi()
        if not question_type:
            return

        self.pelaa_pelia(game_mode, question_type)

    def valitse_pelimoodi(self):

        while True:
            choice = self.menu_renderer.nayta_pelimoodi_valikko()

            if choice == '1':
                return GameMode.CLASSIC
            elif choice == '2':
                return GameMode.SUDDEN_DEATH
            elif choice == '3':
                return GameMode.TIME_ATTACK
            elif choice == '4':
                return None

    def valitse_kysymystyyppi(self):

        while True:
            choice = self.menu_renderer.nayta_kysymystyyppivalikko()

            if choice == '1':
                return QuestionType.AIRPORT_ELEVATION
            elif choice == '2':
                return QuestionType.COUNTRY_POPULATION
            elif choice == '3':
                return None

    def pelaa_pelia(self, game_mode, question_type):

        self.Peli_intro(game_mode, question_type)
        input("Paina Enter aloittaaksesi...")

        self.game.aloita_uusi_peli(self.player_id, self.username, question_type, game_mode)

        if not self.validate_game_start():
            return

        self.aja_peli_loop(question_type)

    def Peli_intro(self, game_mode, question_type):

        if question_type == QuestionType.AIRPORT_ELEVATION:
            title = "LENTOKENTTIEN KORKEUDET"
        else:
            title = "MAIDEN VÄKILUVUT"

        print("\n" + "=" * 60)
        print(f" {title} ")
        print("=" * 60)

        if game_mode == GameMode.CLASSIC:
            print("Klassinen tila - 3 elämää\nArvaa, onko seuraava arvo HIGHER vai LOWER!")
        elif game_mode == GameMode.SUDDEN_DEATH:
            print("ÄKKIKUOLEMA - 1 elämä!\nYksi virhe päättää pelin!")
        else:
            print("AIKARAJA - 60 sekuntia!\n1 elämä, 60 sekuntia aikaa!")

        print("Onnea matkaan!\n")

    def validate_game_start(self):

        if not self.game.state.current_item or not self.game.state.next_item:
            print("\nVirhe: Ei voitu hakea tietoja!")
            return False
        return True

    def aja_peli_loop(self, question_type):

        while not self.game.state.game_over and not self.quit_requested:
            display_info = self.game.get_current_display()

            self.game_display.show_game_header(display_info)
            self.game_display.show_game_content(display_info, question_type)

            player_choice = self.get_player_input()
            if player_choice == 'q':
                self.quit_requested = True
                print("\nPeli keskeytetty.")
                return

            self.prosessoi_pelaajan_vastaus(player_choice)

        self.handle_game_end()

    def get_player_input(self):

        while True:
            choice = input("\nOnko seuraava HIGHER vai LOWER? (h/l) tai (q lopettaaksesi): ").lower()
            if choice in ['h', 'l', 'q']:
                return choice
            print("Virheellinen valinta! Valitse h, l tai q.")

    def prosessoi_pelaajan_vastaus(self, choice):

        is_higher = choice == 'h'
        correct, message = self.game.arvaus(is_higher)

        print(f"\n{'✓' if correct else '✗'} {message}")


        if (self.game.state.game_over and
                self.game.state.game_mode == GameMode.TIME_ATTACK and
                self.game.state.time_remaining <= 0):
            print(f"\nAIKA LOPPUI! Saavutit {self.game.state.score} pistettä!")
            return

        if not correct and not self.game.state.game_over:
            input("\nPaina Enter jatkaaksesi...")

    def handle_game_end(self):

        if (self.game.state.game_over and
                self.game.state.game_mode != GameMode.TIME_ATTACK and
                not self.quit_requested):
            input("\nPaina Enter palataksesi valikkoon...")

    def handle_leaderboard_option(self):

        choice = self.menu_renderer.nayta_pistetaulukko_pelimoodi()

        if choice == '1':
            self.statistics_renderer.nayta_pistetaulukko(self.db, 'classic')
        elif choice == '2':
            self.statistics_renderer.nayta_pistetaulukko(self.db, 'sudden_death')
        elif choice == '3':
            self.statistics_renderer.nayta_pistetaulukko(self.db, 'time_attack')


def main():

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