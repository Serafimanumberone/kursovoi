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

