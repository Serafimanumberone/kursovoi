# price.py
from flask import flash, request, redirect, url_for, jsonify
from psycopg2._psycopg import connection
from add import execute_query

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
