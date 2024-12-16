import os
import smtplib
from collections import defaultdict
from email.header import Header
from email.mime.text import MIMEText
from io import BytesIO
from openpyxl import Workbook
from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify, send_file, make_response
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import host, user, password, db_name
from admin import db_params
from add import execute_query, add_master_to_db
import plotly.graph_objs as go
kur = Flask(__name__)
kur.secret_key = 'buivol3000'
connection = None

try:
    # Подключение к существующей базе данных
    with psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
    ) as connection:
        connection.autocommit = True

        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            print(f"Версия сервера: {cursor.fetchone()}")

            # Создание новой таблицы
            with connection.cursor() as cursor_clients:
                cursor.execute(
                    """CREATE TABLE IF NOT EXISTS clients(
                      id serial PRIMARY KEY,
                      surname varchar(50) NOT NULL,
                      name varchar(50) NOT NULL,
                      email VARCHAR(100) UNIQUE NOT NULL,
                      phone VARCHAR(20) NOT NULL,
                      password VARCHAR(150) NOT NULL)"""
                )
                connection.commit()
                print("[INFO] Таблица успешно создана")


        # Функция для создания нового клиента
        def create_client(surname, name, email, phone, password):
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO clients (surname, name, email, phone, password) VALUES (%s, %s, %s, %s, %s)",
                    (surname, name, email, phone, hashed_password))
                connection.commit()


except Exception as ex:
    print("[INFO] Ошибка при работе с PostgreSQL", ex)

finally:
    # Соединение будет автоматически закрыто из-за оператора 'with' выше
    pass


@kur.route('/')
def index():
    return render_template('index.html')

@kur.route('/otprav')
def otprav():
    return render_template('otprav.html')

@kur.route('/podpiska')
def podpiska():
    return render_template('podpiska.html')

@kur.route('/about')
def about():
    return render_template('about.html')

@kur.route('/kartinki_master')
def kartinki_master():
    master_data = get_master_data()
    return render_template('kartinki_master.html',  master_data=master_data)

@kur.route('/master')
def master():
    master_data = get_master_data()
    return render_template('master.html', master_data=master_data)


@kur.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        surname = request.form['surname']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Ваша функция для создания клиента (create_client)
        create_client(surname, name, email, phone, password)

        session['email'] = email
        client = get_client_by_email(email)
        session['role'] = 'client' if client else 'admin'  # Установите роль
        flash('Registration successful!', category='success')
        return redirect(url_for('signin'))

    return render_template('signup.html')


def get_client_by_email(email):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
        return cursor.fetchone()


@kur.route('/reg', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if validate_clients(email, password):
            flash('Logged in successfully!', category='success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', category='error')

    return render_template('reg.html', error=None)


def validate_clients(email, password):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
            client = cursor.fetchone()

            if client:
                stored_hash = client[5]

                if check_password_hash(stored_hash, password):
                    session['id'] = client[0]
                    session['surname'] = client[1]
                    session['name'] = client[2]
                    session['email'] = client[3]
                    session['role'] = 'admin' if client[0] == 2 else 'client'  # Установите роль в сессии
                    return True
                else:
                    return False
            else:
                return False
    except Exception as ex:
        print("[INFO] Error while validating clients", ex)
        return False


@kur.route('/dashboard')
def dashboard():
    if 'surname' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'client':
            return redirect(url_for('client_dashboard'))
    return redirect(url_for('reg'))


@kur.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')


@kur.route('/home')
def home():
    if 'email' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'client':
            return redirect(url_for('client_dashboard'))
    else:
        return redirect(url_for('signin'))


@kur.route('/reg')
def reg():
    return render_template('reg.html')


# ПРОСМОТР ДАННЫХ О МАСТЕРАХ
def get_master_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # выполнение запроса для вывода данных из таблицы master
    cursor.execute("SELECT * FROM master ORDER BY id_m ")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


@kur.route('/info_master')
def display_master():
    master_data = get_master_data()
    return render_template('info_master.html', masters=master_data)


# ДОБАВЛЕНИЕ/ИЗМЕНЕНИЕ/УДАЛЕНИЕ МАСТЕРА/АДМИН
def add_master_to_db(surname, name, job_title, description):
    query = (
        'INSERT INTO public.master ("Surname", "Name", "job_title", "description") '
        'VALUES (%s, %s, %s, %s) RETURNING *'
    )
    params = (surname, name, job_title, description)

    try:
        result = execute_query(query, params, fetchall=True)

        if result:
            added_master = result[0]
            print("[INFO] Master added successfully:", added_master)
            return added_master  # Возвращаем добавленного мастера
        else:
            print("[ERROR] Failed to retrieve added master.")
            return None
    except Exception as ex:
        print("[ERROR] Failed to add master:", ex)
        return None


@kur.route('/add_master', methods=['POST'])
def add_master_route():
    if request.method == 'POST':
        surname = request.form['surname']
        name = request.form['name']
        job_title = request.form['job_title']
        description = request.form['description']

        try:
            # Вызываем функцию для добавления мастера
            added_master = add_master_to_db(surname, name, job_title, description)

            if added_master:
                flash('Мастер успешно добавлен!', category='success')
            else:
                flash('Не удалось добавить мастера. Пожалуйста, попробуйте снова.', category='error')
        except Exception as ex:
            print("[ERROR] Exception during add_master_route:", ex)
            flash('Не удалось добавить мастера. Пожалуйста, попробуйте снова.', category='error')

        # После добавления мастера перенаправляем на страницу с информацией о мастерах
        return redirect(url_for('info_master'))


@kur.route('/edit_master', methods=['POST'])
def edit_master():
    if request.method == 'POST':
        master_id_str = request.form['editMasterId']

        # Проверка, что значение не пустое
        if master_id_str:
            try:
                master_id = int(master_id_str)

                # Используем существующее глобальное подключение
                connection.autocommit = True

                with connection.cursor() as cursor:
                    # обновить данные мастера в базе данных
                    cursor.execute("""
                        UPDATE public.master
                        SET "Surname" = %s, "Name" = %s, "job_title" = %s,  "description" = %s
                        WHERE id_m = %s;
                    """, (
                        request.form['editSurname'],
                        request.form['editName'],
                        request.form['editJobTitle'],

                        request.form['editDescription'],
                        master_id
                    ))
                    # Подтверждение изменений
                    connection.commit()

                return redirect('/info_master')
            except ValueError as ve:
                print(f"Error converting '{master_id_str}' to int: {ve}")

    return redirect('/info_master')


@kur.route('/delete_master/<int:master_id>', methods=['DELETE'])
def delete_master(master_id):
    try:
        cursor = connection.cursor()
        # удаление из базы данных PostgreSQL
        cursor.execute("DELETE FROM public.master WHERE id_m = %s;", (master_id,))
        connection.commit()
        # Закрытие курсора
        cursor.close()
        return jsonify({"success": True, "message": "Мастер успешно удален"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при удалении мастера: {str(e)}"})


# ПРОСМОТР ИНФОРМАЦИИ О КЛИЕНТАХ /АДМИН
def get_clients_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute('SELECT id, surname, name, email, phone FROM clients WHERE id <> 2 ORDER BY id')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows



@kur.route('/info_master', methods=['GET', 'POST'])
def info_master():
    return render_template('info_master.html')


@kur.route('/info_client')
def info_client():
    clients = get_clients_data()
    return render_template('info_client.html', clients=clients)


def get_services_from_db():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    try:
        query = "SELECT id_s, name_category FROM public.services"
        cursor.execute(query)
        services = cursor.fetchall()
        # Если все прошло успешно, коммитим транзакцию
        conn.commit()
        # print("Services from get_services_from_db:", services)
        return services
    except Exception as e:
        # В случае ошибки откатываем транзакцию
        conn.rollback()
        print(f"Error: {e}")
        return []
    finally:
        # Всегда закрываем курсор
        cursor.close()


@kur.route('/client_dashboard', methods=['GET', 'POST'])
def client_dashboard():
    selected_service = None
    selected_master = None

    if request.method == 'POST':
        selected_service = request.form.get('service')
        selected_master = request.form.get('master')
        print("POST Request - Selected service:", selected_service)

        # Получаем данные из формы
        master_id = selected_master
        id_s = request.form.get('service')
        date = request.form.get('date')
        time = request.form.get('time')

        print(f"Received form data: master_id={master_id}, id_s={id_s}, date={date}, time={time}")

        # Переменные для проверки существования услуги и мастера
        service_exists = False
        master_exists = False

        try:
            # Проверка существования id_s в таблице services
            cursor.execute("SELECT * FROM services WHERE id_s = %s", (id_s,))
            service_exists = cursor.fetchone() is not None

            # Проверка существования master_id в таблице master_service
            cursor.execute("SELECT * FROM master_service WHERE master_id = %s", (master_id,))
            master_exists = cursor.fetchone() is not None

            if not service_exists or not master_exists:
                print("Invalid service or master id")
                # Можно добавить дополнительный вывод, в зависимости от вашего предпочтения
                return jsonify({"status": "Error", "message": "Invalid service or master id"})
        except Exception as e:
            print(f"Error in database query: {e}")

        client_id = session.get('id')

        # Вставка данных в таблицу appointment
        conn = None
        try:
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO appointment (id_m, id, id_s, date, time)
                VALUES (%s, %s, %s, %s, %s)
            """, (master_id, client_id, id_s, date, time))

            conn.commit()
            print("Appointment added successfully!")
        except Exception as e:
            print(f"Error inserting appointment to the database: {e}")
            if conn:
                conn.rollback()

        finally:
            if conn:
                conn.close()

    masters = fetch_masters_data_client(connection, selected_service)
    print("Masters after fetch_masters_data_client:", masters)

    services = get_services_from_db()

    return render_template('client_dashboard.html', services=services, masters=masters,
                           selected_service=selected_service)


def fetch_masters_data_client(conn, selected_service):
    try:
        print("Selected service in fetch_masters_data_client:", selected_service)  # Отладочный вывод
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id_m, \"Surname\" FROM public.master "
                "WHERE id_m IN (SELECT master_id FROM public.master_service WHERE service_id = %s)",
                (selected_service,)
            )
            masters = cursor.fetchall()
            # print("Masters from fetch_masters_data:", masters)  # Отладочный вывод
            return masters
    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL", ex)
        return []


# ПРОСМОТР ИНФЫ ОБ УСЛУГАХ АДМИН
@kur.route('/info_service')
def info_service():
    services = get_service_data()
    return render_template('info_service.html', services=services)


def get_service_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute('SELECT id_s, name_category, description FROM services ORDER BY id_s')

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# ПРОСМОТР ИНФЫ ОБ УСЛУГАХ КЛИЕНТ
@kur.route('/uslug')
def uslug():
    services = get_service_data()
    return render_template('uslug.html', services=services)


def get_service_data_uslug():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute('SELECT name_category, description FROM services ORDER BY id_s')

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# ДОБАВИТЬ/ИЗМЕНИТЬ/УДАЛИТЬ
def add_service_to_db(name_category, description):
    query = (
        'INSERT INTO public.services (name_category, description) '
        'VALUES (%s, %s) RETURNING *'
    )
    params = (name_category, description)

    try:
        result = execute_query(query, params, fetchall=True)

        if result:
            added_service = result[0]
            print("[INFO] Service added successfully:", added_service)
            return added_service
        else:
            print("[ERROR] Failed to retrieve added service.")
            return None
    except Exception as ex:
        print("[ERROR] Failed to add service:", ex)
        return None


@kur.route('/add_service', methods=['POST'])
def add_service_route():
    if request.method == 'POST':
        name_category = request.form['name_category']
        description = request.form['description']

        try:
            # Вызываем функцию для добавления мастера
            added_service = add_service_to_db(name_category, description)

            if added_service:
                flash('Услуга успешно добавлена!', category='success')
            else:
                flash('Не удалось добавить услугу. Пожалуйста, попробуйте снова.', category='error')
        except Exception as ex:
            print("[ERROR] Exception during add_service_route:", ex)
            flash('Не удалось добавить услугу. Пожалуйста, попробуйте снова.', category='error')

        # После добавления мастера перенаправляем на страницу с информацией о мастерах
        return redirect(url_for('info_service'))


@kur.route('/edit_service', methods=['POST'])
def edit_service():
    if request.method == 'POST':
        service_id_str = request.form['editServiceId']

        # Проверка, что значение не пустое
        if service_id_str:
            try:
                service_id = int(service_id_str)

                # Используем существующее глобальное подключение
                connection.autocommit = True

                with connection.cursor() as cursor:
                    # обновить данные  в базе данных
                    cursor.execute("""
                        UPDATE public.services
                        SET "name_category" = %s,"description" = %s
                        WHERE id_s = %s;
                    """, (
                        request.form['editNameCategory'],
                        request.form['editDescription'],
                        service_id
                    ))
                    # Подтверждение изменений
                    connection.commit()

                return redirect('/info_service')
            except ValueError as ve:
                print(f"Error converting '{service_id_str}' to int: {ve}")

    return redirect('/info_service')


@kur.route('/delete_service/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    try:
        cursor = connection.cursor()
        # удаление из базы данных PostgreSQL
        cursor.execute("DELETE FROM public.services WHERE id_s = %s;", (service_id,))
        connection.commit()
        # Закрытие курсора
        cursor.close()
        return jsonify({"success": True, "message": "Услуга успешно удалена"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при удалении услуги: {str(e)}"})


@kur.route('/history')
def history():
    try:
        conn = psycopg2.connect(**db_params)
        with conn.cursor() as cursor:
            # Выполните запрос для извлечения данных из таблицы appointment
            client_id = session.get('id')

            query = """
                SELECT a.id_a, m."Surname" as master_name, c."surname" as client_name, s.name_category as service_name, a.date, a.time
                FROM public.appointment a
                INNER JOIN public.master m ON a.id_m = m.id_m
                INNER JOIN public.clients c ON a.id = c.id
                INNER JOIN public.services s ON a.id_s = s.id_s
                WHERE a.id = %s
            """
            cursor.execute(query, (client_id,))

            appointments = cursor.fetchall()

        return render_template('history.html', appointments=appointments)
    except Exception as e:
        print(f"Error fetching order history: {e}")
        return render_template('history.html', appointments=[])


@kur.route('/zakaz')
def zakaz():
    try:
        conn = psycopg2.connect(**db_params)
        with conn.cursor() as cursor:
            # Выполните запрос для извлечения всех данных из таблицы appointment
            query = """SELECT a.id_a, m."Surname" as master_name, c."surname" as client_name, s.name_category as 
            service_name, a.date, a.time FROM public.appointment a INNER JOIN public.master m ON a.id_m = m.id_m 
            INNER JOIN public.clients c ON a.id = c.id INNER JOIN public.services s ON a.id_s = s.id_s"""
            cursor.execute(query)

            appointments = cursor.fetchall()

        return render_template('zakaz.html', appointments=appointments)
    except Exception as e:
        print(f"Error fetching order history: {e}")
        return render_template('zakaz.html', appointments=[])


# ДОБАВИТЬ/ИЗМЕНИТЬ/УДАЛИТЬ ЗАКАЗ
def add_appointment_to_db(master_id, client_id, service_id, date, time):
    query = (
        'INSERT INTO public.appointment (id_m, id, id_s, date, time) '
        'VALUES (%s, %s, %s, %s, %s) RETURNING *'
    )
    params = (master_id, client_id, service_id, date, time)

    try:
        result = execute_query(query, params, fetchall=True)

        if result:
            added_appointment = result[0]
            print("[INFO] Appointment added successfully:", added_appointment)
            return added_appointment
        else:
            print("[ERROR] Failed to retrieve added appointment.")
            return None
    except Exception as ex:
        print("[ERROR] Failed to add appointment:", ex)
        return None


@kur.route('/add_appointment', methods=['POST'])
def add_appointment_route():
    if request.method == 'POST':
        master_id = request.form['master_id']
        client_id = request.form['client_id']
        service_id = request.form['service_id']
        date = request.form['date']
        time = request.form['time']

        try:
            # Вызываем функцию для добавления заказа
            added_appointment = add_appointment_to_db(master_id, client_id, service_id, date, time)

            if added_appointment:
                flash('Заказ успешно добавлен!', category='success')
            else:
                flash('Не удалось добавить заказ. Пожалуйста, попробуйте снова.', category='error')
        except Exception as ex:
            print("[ERROR] Exception during add_appointment_route:", ex)
            flash('Не удалось добавить заказ. Пожалуйста, попробуйте снова.', category='error')

        # После добавления заказа перенаправляем на страницу с информацией о заказах
        return redirect(url_for('zakaz'))


@kur.route('/edit_appointment', methods=['POST'])
def edit_appointment():
    if request.method == 'POST':
        appointment_id_str = request.form['editAppointmentId']

        # Проверка, что значение не пустое
        if appointment_id_str:
            try:
                appointment_id = int(appointment_id_str)

                # Используем существующее глобальное подключение
                connection.autocommit = True

                with connection.cursor() as cursor:
                    # Обновить данные в базе данных
                    cursor.execute("""
                        UPDATE public.appointment
                        SET "id_m" = %s, "id" = %s, "id_s" = %s, "date" = %s, "time" = %s
                        WHERE id_a = %s;
                    """, (
                        request.form['editMasterId'],
                        request.form['editClientId'],
                        request.form['editServiceId'],
                        request.form['editDate'],
                        request.form['editTime'],
                        appointment_id
                    ))
                    # Подтверждение изменений
                    connection.commit()

                return redirect('/zakaz')
            except ValueError as ve:
                print(f"Error converting '{appointment_id_str}' to int: {ve}")

    return redirect('/zakaz')


@kur.route('/delete_appointment/<int:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    try:
        cursor = connection.cursor()
        # Удаление из базы данных PostgreSQL
        cursor.execute("DELETE FROM public.appointment WHERE id_a = %s;", (appointment_id,))
        connection.commit()
        # Закрытие курсора
        cursor.close()
        return jsonify({"success": True, "message": "Заказ успешно удален"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при удалении заказа: {str(e)}"})


@kur.route('/get_appointment/<int:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    try:
        conn = psycopg2.connect(**db_params)
        with conn.cursor() as cursor:
            query = """
                SELECT id_a, id_m, id, id_s, date, time
                FROM public.appointment
                WHERE id_a = %s
            """
            cursor.execute(query, (appointment_id,))
            appointment = cursor.fetchone()

        if appointment:
            return jsonify({"success": True, "appointment": {
                "id_a": appointment[0],
                "id_m": appointment[1],
                "id": appointment[2],
                "id_s": appointment[3],
                "date": str(appointment[4]),
                "time": str(appointment[5])
            }})
        else:
            return jsonify({"success": False, "message": "Заказ не найден"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при получении данных о заказе: {str(e)}"})


@kur.route('/review', methods=['GET', 'POST'])
def review():
    if request.method == 'POST':
        try:
            # Подключение к базе данных
            with psycopg2.connect(**db_params) as conn:
                # Открываем курсор для выполнения SQL-запросов
                with conn.cursor() as cursor:
                    # Получаем данные из формы
                    comment = request.form.get('review')
                    grade = int(request.form.get('grade'))

                    # Выполняем SQL-запрос для добавления отзыва в базу данных
                    cursor.execute("INSERT INTO public.review (comment, grade) VALUES (%s, %s)", (comment, grade))
                    # Фиксируем изменения
                    conn.commit()

        except Exception as e:
            # Обрабатываем возможные ошибки
            print(f"Error while leaving a review: {e}")

        return redirect(url_for('review'))

    try:
        # Подключение к базе данных для извлечения отзывов
        with psycopg2.connect(**db_params) as conn:
            # Открываем курсор для выполнения SQL-запросов
            with conn.cursor() as cursor:
                # Выполняем SQL-запрос для извлечения отзывов из базы данных
                cursor.execute("SELECT id_r, comment, grade FROM public.review")
                reviews = cursor.fetchall()

    except Exception as e:
        # Обрабатываем возможные ошибки
        print(f"Error while fetching reviews: {e}")
        reviews = []

    return render_template('review.html', reviews=reviews)


# ПРОСМОТР/УДАЛЕНИЕ/ИЗМЕНЕНИЕ/ДОБАВЛЕНИЕ ПРАЙСА
# ПРОСМОТР ДАННЫХ О ПРАЙС-ЛИСТЕ
def get_price_list_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # выполнение запроса для вывода данных из таблицы price_list
    cursor.execute("SELECT * FROM public.price_list ORDER BY id_p")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


@kur.route('/info_price_list')
def info_price_list():
    price_list_data = get_price_list_data()
    return render_template('info_price_list.html', price_list=price_list_data)


# ДОБАВЛЕНИЕ/ИЗМЕНЕНИЕ/УДАЛЕНИЕ ПОЗИЦИИ В ПРАЙС-ЛИСТЕ
def add_price_list_to_db(service_id, price):
    query = (
        'INSERT INTO public.price_list ("id_s", "price") '
        'VALUES (%s, %s) RETURNING *'
    )
    params = (service_id, price)

    try:
        result = execute_query(query, params, fetchall=True)

        if result:
            added_price = result[0]
            print("[INFO] Price added successfully:", added_price)
            return added_price  # Возвращаем добавленную позицию в прайс-листе
        else:
            print("[ERROR] Failed to retrieve added price.")
            return None
    except Exception as ex:
        print("[ERROR] Failed to add price:", ex)
        return None


@kur.route('/add_price_list', methods=['POST'])
def add_price_list_route():
    if request.method == 'POST':
        service_id = request.form['serviceId']
        price = request.form['price']

        try:
            # Вызываем функцию для добавления позиции в прайс-лист
            added_price = add_price_list_to_db(service_id, price)

            if added_price:
                flash('Позиция в прайс-листе успешно добавлена!', category='success')
            else:
                flash('Не удалось добавить позицию в прайс-лист. Пожалуйста, попробуйте снова.', category='error')
        except Exception as ex:
            print("[ERROR] Exception during add_price_list_route:", ex)
            flash('Не удалось добавить позицию в прайс-лист. Пожалуйста, попробуйте снова.', category='error')

        # После добавления позиции в прайс-лист перенаправляем на страницу с информацией о прайс-листе
        return redirect(url_for('info_price_list'))


@kur.route('/edit_price_list', methods=['POST'])
def edit_price_list():
    if request.method == 'POST':
        price_id_str = request.form['editPriceId']

        # Проверка, что значение не пустое
        if price_id_str:
            try:
                price_id = int(price_id_str)

                # Используем существующее глобальное подключение
                connection.autocommit = True

                with connection.cursor() as cursor:
                    # обновить данные позиции в прайс-листе в базе данных
                    cursor.execute("""
                        UPDATE public.price_list
                        SET "id_s" = %s, "price" = %s
                        WHERE id_p = %s;
                    """, (
                        request.form['editServiceId'],
                        request.form['editPrice'],
                        price_id
                    ))
                    # Подтверждение изменений
                    connection.commit()

                return redirect('/info_price_list')
            except ValueError as ve:
                print(f"Error converting '{price_id_str}' to int: {ve}")

    return redirect('/info_price_list')


@kur.route('/delete_price_list/<int:price_id>', methods=['DELETE'])
def delete_price_list(price_id):
    try:
        cursor = connection.cursor()
        # удаление из базы данных PostgreSQL
        cursor.execute("DELETE FROM public.price_list WHERE id_p = %s;", (price_id,))
        connection.commit()
        # Закрытие курсора
        cursor.close()
        return jsonify({"success": True, "message": "Запись успешно удалена из прайс-листа"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при удалении записи из прайс-листа: {str(e)}"})


# ГЛЯНУТЬ ПРАЙС ЛИСТ НА ОБЫЧНОМ САЙТЕ
def get_price_list_data_basik():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Выполнение запроса для вывода данных из таблицы price_list с объединением services
    cursor.execute("""
        SELECT pl.id_p, s.name_category, pl.price
        FROM public.price_list pl
        JOIN public.services s ON pl.id_s = s.id_s
        ORDER BY pl.id_p
    """)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


@kur.route('/info_price_basik', methods=['GET', 'POST'])
def info_price_basik():
    try:
        # Получение данных о прайс-листе
        price_list_data = get_price_list_data_basik()

        # Передача данных в шаблон
        return render_template('info_price_basik.html', price_list=price_list_data)
    except Exception as e:
        # Обработка ошибок, если они возникнут
        print(f"Error in info_price_basik: {e}")
        return render_template('error_page.html', error_message='Произошла ошибка при загрузке данных о прайс-листе.')


#ДЛЯ EXCEL
def get_masters_data_ex():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    try:
        query = "SELECT id_m, \"Surname\" FROM public.master"
        cursor.execute(query)
        masters = cursor.fetchall()
        return masters
    except Exception as e:
        print(f"Error fetching masters data: {e}")
        return []
    finally:
        cursor.close()


def get_clients_data_ex():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    try:
        query = "SELECT id, \"surname\" FROM public.clients"
        cursor.execute(query)
        clients = cursor.fetchall()
        return clients
    except Exception as e:
        print(f"Error fetching clients data: {e}")
        return []
    finally:
        cursor.close()

def get_services_ex():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    try:
        query = "SELECT id_s, name_category FROM public.services"
        cursor.execute(query)
        services = cursor.fetchall()
        return services
    except Exception as e:
        print(f"Error fetching services data: {e}")
        return []
    finally:
        cursor.close()
def get_appointments_data_ex():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    try:
        query = """
            SELECT a.id_a, m."Surname" as master_name, c."surname" as client_name,
                   s.name_category as service_name, a.date, a.time
            FROM public.appointment a
            INNER JOIN public.master m ON a.id_m = m.id_m
            INNER JOIN public.clients c ON a.id = c.id
            INNER JOIN public.services s ON a.id_s = s.id_s
        """
        cursor.execute(query)
        appointments = cursor.fetchall()

        # Сортировка по id_a
        sorted_appointments = sorted(appointments, key=lambda x: x[0])

        return sorted_appointments
    except Exception as e:
        print(f"Error fetching appointments data: {e}")
        return []
    finally:
        cursor.close()

# Function to generate Excel file with additional statistics
def generate_excel_with_stats():
    # Создаем объект BytesIO для хранения Excel-файла
    excel_buffer = BytesIO()

    # Используем данные о записях для создания Excel-файла
    appointments_data = get_appointments_data_ex()

    # Используем данные об услугах из базы данных
    services_data = get_services_ex()

    # Создаем книгу Excel и выбираем активный лист
    workbook = Workbook()
    sheet = workbook.active

    # Добавляем заголовки в лист Excel
    headers = ["ID записи", "Мастер", "Клиент", "Услуга", "Дата", "Время"]
    sheet.append(headers)

    # Добавляем данные о записях в лист Excel
    for appointment in appointments_data:
        sheet.append([
            appointment[0],  # ID записи
            appointment[1],  # Мастер
            appointment[2],  # Клиент
            appointment[3],  # Услуга
            appointment[4],  # Дата
            appointment[5],  # Время
        ])

    # Вычисляем статистику
    service_count = defaultdict(int)
    master_count = defaultdict(int)
    client_order_count = defaultdict(int)

    for appointment in appointments_data:
        service_count[appointment[3]] += 1
        master_count[appointment[1]] += 1
        client_order_count[appointment[2]] += 1

    # Добавляем статистику в лист Excel
    sheet.append([])  # Добавляем пустую строку для разделения
    sheet.append(["Услуга", "Количество записей"])

    # Используем данные об услугах из базы данных для дополнения статистики
    for service_id, service_name in services_data:
        service_name = service_name or 'Неизвестная услуга'
        sheet.append([service_name, service_count.get(service_name, 0)])

    sheet.append([])  # Добавляем пустую строку для разделения
    sheet.append(["Мастер", "Количество записей"])
    for master, count in master_count.items():
        sheet.append([master, count])

    sheet.append([])  # Добавляем пустую строку для разделения
    sheet.append(["Клиент", "Общее количество записей"])
    for client, count in client_order_count.items():
        sheet.append([client, count])

    # Сохраняем Excel-файл в буфере BytesIO
    workbook.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer


@kur.route('/download_excel_with_stats')
def download_excel_with_stats():
    try:
        # Генерируем Excel-файл
        excel_buffer = generate_excel_with_stats()

        # Создаем объект Response
        response = make_response(send_file(
            excel_buffer,
            as_attachment=True,
            download_name='statistics.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ))

        # Устанавливаем заголовки
        response.headers['Content-Disposition'] = 'attachment; filename=statistics.xlsx'

        return response

    except Exception as e:
        return str(e)

@kur.route('/save_changes', methods=['POST'])
def save_changes():
    data = request.json
    image_updates = data.get('imageUpdates', [])
    return jsonify({"message": "Изменения успешно сохранены"})






@kur.route('/get_service_price', methods=['POST'])
def get_service_price():
    service_id = request.form.get('id_s')  # ID выбранной услуги
    price_id = request.form.get('id_p')      # ID цены (например, из выпадающего списка)

    if not service_id or not price_id:
        return jsonify({"error": "ID услуги или ID цены не указаны"}), 400

    try:
        # Выполняем запрос для получения цены из price_list на основе id_s и id_p
        query = "SELECT price FROM price_list WHERE id_s = %s AND id_p = %s"
        cursor.execute(query, (service_id, price_id))
        price = cursor.fetchone()

        if price:
            return jsonify({"price": price[0]})
        else:
            return jsonify({"error": "Цена не найдена"}), 404

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500


def send_ya_mail(recipients_emails: list, msg_text: str):
    login = 'dashokbuivol@yandex.ru'
    password = 'qfvoyccymzjywwxh'

    msg = MIMEText(f'{msg_text}', 'plain', 'utf-8')
    msg['Subject'] = Header('Салон Дарья!', 'utf-8')
    msg['From'] = login
    msg['To'] = ', '.join(recipients_emails)

    s = smtplib.SMTP('smtp.yandex.ru', 587, timeout=10)

    try:
        s.starttls()
        s.login(login, password)
        s.sendmail(msg['From'], recipients_emails, msg.as_string())
    except Exception as ex:
        print(ex)
    finally:
        s.quit()

@kur.route('/podpiska', methods=['POST'])
def subscribe():
    email = request.form['email']

    # Подключаемся к базе данных и сохраняем email
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Вставляем email в таблицу
        cursor.execute("INSERT INTO subscriptions (email) VALUES (%s)", (email,))
        conn.commit()

        # Получаем последний добавленный email
        cursor.execute("SELECT email FROM subscriptions ORDER BY id DESC LIMIT 1")
        last_subscriber = cursor.fetchone()[0]

        # Отправляем письмо последнему подписавшемуся
        send_ya_mail([last_subscriber], 'Спасибо за подписку на нашу рассылку!')

        cursor.close()
        conn.close()

        flash('Вы успешно подписались на рассылку!', 'success')
        return redirect(url_for('index'))  # Перенаправление на главную страницу
    except Exception as e:
        print(f'Error: {e}')
        flash('Произошла ошибка при подписке. Попробуйте снова.', 'error')
        return redirect(url_for('index'))  # Перенаправление на главную страницу


@kur.route('/send_message', methods=['POST'])
def send_message():
    try:
        message = request.form['message']
        recipients = get_all_subscribers()

        if not recipients:
            flash('Нет подписчиков для рассылки.', 'error')
            return redirect(url_for('otprav'))  # Перенаправляем на страницу рассылки

        # Отправка email всем подписчикам
        send_ya_mail(recipients, message)
        flash('Сообщение успешно отправлено всем подписчикам!', 'success')

        return redirect(url_for('otprav'))  # Перенаправляем на страницу рассылки
    except Exception as e:
        print(f"Error: {e}")
        flash('Произошла ошибка при отправке сообщения. Попробуйте снова.', 'error')
        return redirect(url_for('otprav'))  # Перенаправляем на страницу рассылки

def get_all_subscribers():
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Выполняем запрос для получения всех email-адресов из таблицы подписок
        cursor.execute("SELECT email FROM subscriptions")
        subscribers = cursor.fetchall()

        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()

        # Возвращаем список email-адресов
        return [subscriber[0] for subscriber in subscribers]  # Возвращаем только email из каждого кортежа
    except Exception as e:
        print(f"Error: {e}")
        return []  # Если произошла ошибка, возвращаем пустой список






# Функция для создания графика с помощью Plotly и возврата JSON-строки
def generate_plot(data_dict, title):
    data = [go.Bar(x=list(data_dict.keys()), y=list(data_dict.values()))]
    layout = go.Layout(title=title)
    fig = go.Figure(data=data, layout=layout)
    plot_json = fig.to_json()
    return plot_json

# Функция для отображения страницы с графиками
@kur.route('/stats')
def show_stats():
    try:
        # Генерируем Excel-файл с данными
        excel_buffer = generate_excel_with_stats()

        # Используем данные статистики
        service_count = defaultdict(int)
        master_count = defaultdict(int)
        client_order_count = defaultdict(int)

        for appointment in get_appointments_data_ex():
            service_count[appointment[3]] += 1
            master_count[appointment[1]] += 1
            client_order_count[appointment[2]] += 1

        # Создаем графики для статистики
        service_fig = generate_plot(service_count, "Статистика по услугам")
        master_fig = generate_plot(master_count, "Статистика по мастерам")
        client_fig = generate_plot(client_order_count, "Статистика по клиентам")

        # Передаем графики на страницу HTML с использованием шаблона
        return render_template('stats.html', service_fig=service_fig, master_fig=master_fig, client_fig=client_fig)

    except Exception as e:
        return str(e)




UPLOAD_FOLDER = 'static/uploads/'
kur.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@kur.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify(success=False), 400

    file = request.files['image']
    master_id = request.form.get('masterId')

    if file.filename == '':
        return jsonify(success=False), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(kur.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Сохранение пути к изображению в базе данных можно реализовать здесь

        return jsonify(success=True, imageUrl=f'/{filepath}')

    return jsonify(success=False), 400

if __name__ == "__main__":
    kur.run(debug=True)
