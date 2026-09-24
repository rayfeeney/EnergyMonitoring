from dotenv import load_dotenv

from energymonitoring.database.connection import get_connection


def main():
    load_dotenv()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS DatabaseName;")
            row = cursor.fetchone()

            print("Connected successfully")
            print(f"Database: {row['DatabaseName']}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()