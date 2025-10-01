import mysql.connector
from geopy.distance import geodesic

yhteys = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    database='flight_game',
    user='root',
    password='Python',
    autocommit=True
)

cursor = yhteys.cursor()

def hae_koordinaatit(icao):
    sql = "SELECT latitude_deg, longitude_deg FROM airport WHERE ident = %s"
    cursor.execute(sql, (icao,))
    tulos = cursor.fetchone()
    if tulos:
        return (float(tulos[0]), float(tulos[1]))
    return None