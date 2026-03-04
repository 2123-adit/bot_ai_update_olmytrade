import mysql.connector
import json

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'robot_trading'
}

def check_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        c = conn.cursor(dictionary=True)
        c.execute('''
            SELECT market, tanggal, CONCAT(waktu) as waktu, COUNT(*) as c 
            FROM market_histories 
            GROUP BY market, tanggal, CONCAT(waktu) 
            HAVING c > 1
        ''')
        dupes = c.fetchall()
        
        with open('out.json', 'w') as f:
            json.dump({"dupes": dupes}, f, indent=2)
            
        c.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_db()
