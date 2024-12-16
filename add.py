from flask import Flask, render_template, url_for, request, redirect, session, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from config import host, user, password, db_name


# Ваш метод execute_query с обновлением
def execute_query(query, params=None, fetchall=False):
    connection = None
    result = None

    try:
        with psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        ) as connection:
            connection.autocommit = True

            with connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetchall:
                    result = cursor.fetchall()
                else:
                    result = cursor.fetchone()

    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL", ex)

    return result

# Ваша функция для добавления мастера с улучшенным отслеживанием ошибок
def add_master_to_db(surname, name, job_title, description):
    query = (
        'INSERT INTO public.master ("Surname", "Name", "job_title", "description") '
        'VALUES (%s, %s, %s, %s) RETURNING *'
    )
    params = (surname, name, job_title,  description)

    try:
        # Используем fetchall=True, так как операция INSERT может вернуть несколько строк
        result = execute_query(query, params, fetchall=True)

        if result:
            added_master = result[0]
            print("[INFO] Master added successfully:", added_master)
        else:
            print("[ERROR] Failed to retrieve added master. Result is empty.")
    except psycopg2.Error as ex:
        print("[ERROR] psycopg2 database error:", ex)
        print("[ERROR] psycopg2 error details:", ex.pgcode, ex.pgerror, ex.pgcode, ex.pgerror, ex.diag.message_primary)
    except Exception as ex:
        print("[ERROR] Failed to add master:", ex)

