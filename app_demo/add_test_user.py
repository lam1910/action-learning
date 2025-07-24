import bcrypt
import psycopg2

DB_CONFIG = {
    # This is the 1 time run, please fill in the content first
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def register_user(user_name, email, password, user_role):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO "user" (user_name, email, password, user_role)
                   VALUES (%s, %s, %s, %s)
                   """, (user_name, email, hashed, user_role))
    conn.commit()
    cursor.close()
    conn.close()


register_user('micro_proc', 'lamnn1910@outlook.com', 'arduino_nano_1', 'micro')
register_user('ngoc-lam.nguyen', 'ngoc-lam.nguyen@epita@fr', 'ngoc-lam.nguyen', 'data-engineer')
register_user('grishmareddy.narigela', 'grishmareddy.narigela@epita.fr', 'grishmareddy.narigela', 'data-analyst')
register_user('jatinkumar-keshabhai.parmar', 'jatinkumar-keshabhai.parmar@epita.fr', 'jatinkumar-keshabhai.parmar',
              'data-scientist')
register_user('revanth.puvaneswaran', 'revanth.puvaneswaran@epita.fr', 'revanth.puvaneswaran', 'embedding-engineer')
