from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.secret_key = 'polahidupsehat'
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='dietrecomendation'
app.config['MYSQL_OPTIONS'] = {
    'ssl': {
        'fake_flag': True,  
    }
}
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user_dashboard')
def user_dashboard():
    if session.get('loggedin') and session.get('actor') == '2':
        return render_template('user_dashboard.html')
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('loggedin') and session.get('actor') == '1':
        return render_template('admin_dashboard.html')
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))

@app.route('/profile')
def profile():
    return "<h2>profile</h2>"

@app.route('/recomendation')
def recomendation():
    return "<h2>recomendation</h2>"



@app.route('/plandiet')
def plandiet():
     return render_template('plandiet.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM user WHERE email=%s', (email,))
        akun = cursor.fetchone()

        if akun is None:
            flash('Login Gagal, Cek Username/E-Mail Anda', 'danger')
        elif not check_password_hash(akun[3], password):
            flash('Login Gagal, Cek Password Anda', 'danger')
        else:
            session['loggedin'] = True
            session['email'] = akun[1]
            session['actor'] = akun[5]  
            
            if session['actor'] == '2':  
                return redirect(url_for('user_dashboard'))
            elif session['actor'] == '1':  # Admin
                return redirect(url_for('admin_dashboard'))
    
    return render_template('login.html')

@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        actor = request.form['actor']

        cursor = mysql.connection.cursor()
        
        cursor.execute('SELECT * FROM user WHERE username=%s OR email=%s', (username, email,))
        akun = cursor.fetchone()  

        if akun is None:
            cursor.execute('INSERT INTO user (email, username, password, name, actor) VALUES (%s, %s, %s, %s, %s)', 
                           (email, username, generate_password_hash(password), name, actor))
            mysql.connection.commit()
            cursor.close()  
            flash('Berhasil Daftar Akun', 'success')
            return redirect(url_for('login'))  
        else:
            flash('Username atau Email sudah terdaftar', 'danger')
            cursor.close()  
    return render_template('signup.html')

@app.route('/logout')
def logout():
     session.pop('loggedin',None)
     session.pop('email',None)
     session.pop('actor',None)
     return redirect(url_for('index'))


@app.route('/forgetpass')
def forgetpass():
     return render_template('forgetpass.html')

@app.route('/pengguna')
def pengguna():
                          
    return render_template('pengguna.html',active_page='pengguna')

@app.route('/add_pengguna')
def add_pengguna():
                          
    return render_template('add_pengguna.html',active_page='pengguna')


@app.route('/recipe')
def recipe():
     return render_template('recipe.html',active_page='recipe')

@app.route('/add_recipe')
def add_recipe():
                          
    return render_template('add_recipe.html',active_page='recipe')

@app.route('/food')
def food():
     return render_template('food.html',active_page='food')

@app.route('/add_food')
def add_food():
                          
    return render_template('add_food.html',active_page='food')

@app.route('/article')
def article():
     return render_template('article.html',active_page='article')

@app.route('/add_article')
def add_article():
                          
    return render_template('add_article.html',active_page='article')

if __name__ == '__main__':
    app.run(debug=True)