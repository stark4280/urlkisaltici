from flask import Flask, request, jsonify, redirect, render_template, session, url_for
import sqlite3
import string, random
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "gizli-bir-anahtar"  # Admin paneli için gerekli

# Veritabanı oluştur
def init_db():
    with sqlite3.connect("links.db") as con:
        con.execute('''
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                original TEXT NOT NULL
            )
        ''')

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    url = data.get('longUrl')
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    code = data.get('customCode') or generate_code()

    with sqlite3.connect("links.db") as con:
        cur = con.cursor()
        cur.execute("SELECT original FROM links WHERE code = ?", (code,))
        if cur.fetchone() and not data.get('customCode'):
            code = generate_code()  # Çakışma varsa yeniden üret
        try:
            cur.execute("INSERT INTO links (code, original) VALUES (?, ?)", (code, url))
            con.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Bu kod zaten kullanılıyor."}), 409

    # Sunucu IP'sini veya domain adını kullan
    base_url = request.host_url.rstrip('/')
    return jsonify({"shortUrl": f"{base_url}/{code}"})

@app.route('/<code>')
def redirect_to_original(code):
    with sqlite3.connect("links.db") as con:
        cur = con.cursor()
        cur.execute("SELECT original FROM links WHERE code = ?", (code,))
        row = cur.fetchone()
        if row:
            return redirect(row[0])
        return "Link bulunamadı", 404

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        if request.method == 'POST':
            password = request.form.get('password')
            if password == '1234':
                session['admin_logged_in'] = True
                return redirect(url_for('admin'))
            else:
                return render_template('admin_login.html', error='Hatalı şifre!')
        return render_template('admin_login.html')
    # Giriş başarılıysa, tüm linkleri göster
    with sqlite3.connect("links.db") as con:
        cur = con.cursor()
        cur.execute("SELECT code, original FROM links")
        links = cur.fetchall()
    return render_template('admin_panel.html', links=links)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True) 