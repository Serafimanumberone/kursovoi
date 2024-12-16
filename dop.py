import smtplib
from collections import defaultdict
from email.header import Header
from email.mime.text import MIMEText

import psycopg2
from flask import request, flash, redirect, url_for, render_template

from admin import db_params
from main import kur, generate_excel_with_stats, get_appointments_data_ex


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

    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO subscriptions (email) VALUES (%s)", (email,))
        conn.commit()

        cursor.execute("SELECT email FROM subscriptions ORDER BY id DESC LIMIT 1")
        last_subscriber = cursor.fetchone()[0]

        send_ya_mail([last_subscriber], 'Спасибо за подписку на нашу рассылку!')
        cursor.close()
        conn.close()

        flash('Вы успешно подписались на рассылку!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        print(f'Error: {e}')
        flash('Произошла ошибка при подписке. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@kur.route('/send_message', methods=['POST'])
def send_message():
    try:
        message = request.form['message']
        recipients = get_all_subscribers()

        if not recipients:
            flash('Нет подписчиков для рассылки.', 'error')
            return redirect(url_for('otprav'))

        # Отправка email всем подписчикам
        send_ya_mail(recipients, message)
        flash('Сообщение успешно отправлено всем подписчикам!', 'success')

        return redirect(url_for('otprav'))
    except Exception as e:
        print(f"Error: {e}")
        flash('Произошла ошибка при отправке сообщения. Попробуйте снова.', 'error')
        return redirect(url_for('otprav'))

def get_all_subscribers():
    try:

        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()


        cursor.execute("SELECT email FROM subscriptions")
        subscribers = cursor.fetchall()

        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()


        return [subscriber[0] for subscriber in subscribers]
    except Exception as e:
        print(f"Error: {e}")
        return []


def generate_plot(data_dict, title, go=None):
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