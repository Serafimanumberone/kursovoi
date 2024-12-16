import psycopg2
from flask import render_template, request, flash, redirect, url_for, jsonify, session
from psycopg2._psycopg import connection

from admin import db_params, execute_query
from main import kur, get_services_from_db


@kur.route('/info_master')
def display_master():
    master_data = get_master_data()
    return render_template('info_master.html', masters=master_data)
@kur.route('/master')
def master():
    master_data = get_master_data()
    return render_template('master.html', master_data=master_data)
def get_master_data():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM master ORDER BY id_m ")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
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

@kur.route('/client_dashboard', methods=['GET', 'POST'])
def client_dashboard(cursor=None):
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