from flask import Flask, render_template
import psycopg2

# from main import kur

app = Flask(__name__)


def execute_query(query, params=None, fetchall=False):
    connection = None
    result = None


# Параметры подключения к вашей базе данных
db_params = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'buivol3000',
    'database': 'buivol',
    'port': '5432',  # по умолчанию 5432
}


# Функция для получения данных из таблицы master
def get_master_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Пример выполнения запроса для вывода данных из таблицы master
    cursor.execute("SELECT * FROM master ")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


# @kur.route('/info_master')
# def display_master():
#     master_data = get_master_data()
#     return render_template('info_master.html', masters=master_data)


if __name__ == '__main__':
    app.run(debug=True)
