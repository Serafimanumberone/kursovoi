import psycopg2


def create_tables():
    # Replace these values with your actual database connection parameters
    db_params = {
        'dbname': 'buivol',
        'user': 'postgres',
        'password': 'buivol3000',
        'host': 'localhost',
        'port': '5432',
    }

    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # SQL statements to create tables
        sql_statements = [
            '''
               CREATE TABLE IF NOT EXISTS public.master
               (
                   id_m SERIAL PRIMARY KEY,
                   "Surname" VARCHAR(250),
                   "Name" VARCHAR(250),
                   "job_title" VARCHAR(250),
                   "schedule" VARCHAR(250),
                   "description" VARCHAR(250)
               );

               CREATE TABLE IF NOT EXISTS public.services
               (
                   id_s SERIAL PRIMARY KEY,
                   name_category VARCHAR(250) NOT NULL,
                   description TEXT
               );

               CREATE TABLE IF NOT EXISTS public.appointment
               (
                   id_a SERIAL PRIMARY KEY,
                   id_m INTEGER REFERENCES public.master (id_m),
                   id INTEGER REFERENCES public.clients (id),
                   id_s INTEGER REFERENCES public.services (id_s),
                   date TIMESTAMP WITHOUT TIME ZONE,
                   CONSTRAINT appointment_master_id_fkey FOREIGN KEY (id_m)
                       REFERENCES public.master (id_m) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION,
                   CONSTRAINT appointment_clients_id_fkey FOREIGN KEY (id)
                       REFERENCES public.clients (id) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION,
                   CONSTRAINT appointment_services_id_fkey FOREIGN KEY (id_s)
                       REFERENCES public.services (id_s) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION
               );

               CREATE TABLE IF NOT EXISTS public.review
               (
                   id_r SERIAL PRIMARY KEY,
                   id_m INTEGER REFERENCES public.master (id_m),
                   comment TEXT,
                   grade INTEGER,
                   date DATE,
                   CONSTRAINT review_master_id_fkey FOREIGN KEY (id_m)
                       REFERENCES public.master (id_m) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION
               );

               CREATE TABLE IF NOT EXISTS public.price_list
               (
                   id_p SERIAL PRIMARY KEY,
                   id_s INTEGER REFERENCES public.services (id_s),
                   price DECIMAL(10, 2), 
                   effective_date DATE,
                   category VARCHAR (50),
                   description VARCHAR (250),
                   CONSTRAINT price_list_services_id_fkey FOREIGN KEY (id_s)
                       REFERENCES public.services (id_s) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION
               );

               CREATE TABLE IF NOT EXISTS public.coupons
               (
                   id_co SERIAL PRIMARY KEY,
                   id_s INTEGER REFERENCES public.services (id_s),
                   "Name" VARCHAR(250),
                   activation_code VARCHAR(50) NOT NULL,
                   discount DECIMAL(5, 2) NOT NULL,
                   expiration_date DATE,
                   CONSTRAINT coupons_services_id_fkey FOREIGN KEY (id_s)
                       REFERENCES public.services (id_s) MATCH SIMPLE
                       ON UPDATE NO ACTION
                       ON DELETE NO ACTION
               );
   CREATE TABLE IF NOT EXISTS public.master_service
(
    id_ms SERIAL PRIMARY KEY,
    master_id INT REFERENCES public.master(id_m) ON DELETE CASCADE,
    service_id INT REFERENCES public.services(id_s) ON DELETE CASCADE,
    CONSTRAINT unique_master_service UNIQUE (master_id, service_id)
);


            '''
        ]

        # Execute SQL statements
        for sql_statement in sql_statements:
            try:
                cursor.execute(sql_statement)
                print(f"[INFO] SQL statement executed successfully:\n{sql_statement}")
            except Exception as ex:
                print(f"[ERROR] Failed to execute SQL statement:\n{sql_statement}\nError: {ex}")

        # Commit changes and close connection
        conn.commit()
        print("[INFO] Changes committed successfully")

    except Exception as ex:
        print("[ERROR] Failed to connect to PostgreSQL:", ex)
    finally:
        # Close the connection
        if conn:
            conn.close()
            print("[INFO] Connection closed")


if __name__ == "__main__":
    create_tables()
