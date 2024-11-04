from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_ckeditor import CKEditor
import os

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'polahidupsehat')  


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'dietrecomendation'
app.config['MYSQL_OPTIONS'] = {
    'ssl': {
        'fake_flag': True,
    }
}


mysql = MySQL(app)


ckeditor = CKEditor(app)
app.config['CKEDITOR_PKG_TYPE'] = 'standard'
app.config['CKEDITOR_SERVE_LOCAL'] = False
app.config['CKEDITOR_CDN'] = "https://cdn.ckeditor.com/4.25.0/standard/ckeditor.js"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user_dashboard')
def user_dashboard():
    if session.get('loggedin') and session.get('actor') == '2': 
        userid = session.get('userid')  
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT height, weight, gender, age, goal, activity FROM usercharacteristics WHERE userid = %s", (userid,))
        user_data = cur.fetchone()  
        cur.close()

        no_data_message = ""
        add_userchar = ""

        data_exists = bool(user_data)
        data_dict = {}
        if data_exists:
            height = user_data[0]
            weight = user_data[1]
            gender = user_data[2]
            age = user_data[3]
            goal = user_data[4]
            activity = user_data[5]

            
            height_in_meters = height / 100  
            bmi = weight / (height_in_meters ** 2) if height_in_meters > 0 else "-"

            
            if gender == 'pria':
                bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            elif gender == 'wanita':
                bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
            else:
                bmr = "-"  

            
            data_dict = {
                "height": height or "-",
                "weight": weight or "-",
                "bmi": round(bmi, 2) if isinstance(bmi, (int, float)) else "-",
                "bmr": round(bmr, 2) if isinstance(bmr, (int, float)) else "-",
                "goal": goal or "-",
                "activity": activity or "-"
            }
        else:
           
            no_data_message = "Belum ada data tersedia saat ini. Silakan tambahkan data Anda melalui tombol di bawah ini:"
            add_userchar = url_for('add_userchar')  

        return render_template('user_dashboard.html', data=data_dict, data_exists=data_exists, no_data_message=no_data_message, add_userchar=add_userchar)
    
    
    flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
def admin_dashboard():
    
    if session.get('loggedin') and session.get('actor') == '1':
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM user")
        total_user_count = cur.fetchone()[0]  
        cur.execute("SELECT COUNT(*) FROM recipe")
        total_recipe_count = cur.fetchone()[0] 
        cur.execute("SELECT COUNT(*) FROM article")
        total_article_count = cur.fetchone()[0]  
        return render_template(
            'admin_dashboard.html',
            total_user_count=total_user_count,
            total_recipe_count=total_recipe_count,
            total_article_count=total_article_count
        )
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))



@app.route('/profile')
def profile():
    return "<h2>profile</h2>"

@app.route('/recomendation')
def recomendation():
    return "<h2>recomendation</h2>"

@app.route('/add_userchar')
def add_userchar():
    return "<h2>profile</h2>"


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
            session['userid'] = akun[0]
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
    if session.get('loggedin') and session.get('actor') == '1':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user ORDER BY actor ASC")
        tampilpengguna = cur.fetchall()
        cur.close()
                          
        return render_template('pengguna.html',active_page='pengguna', datapengguna=tampilpengguna)
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))
    

@app.route('/add_penguna', methods=('GET', 'POST'))
def add_pengguna():
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
            return redirect(url_for('pengguna'))  
        else:
            flash('Username atau Email sudah terdaftar', 'danger')
            cursor.close()  
    return render_template('add_pengguna.html',active_page='pengguna')

@app.route('/update_pengguna', methods=['POST'])
def update_pengguna():
    if request.method == "POST":
        userid = request.form['userid']
        username = request.form['username']
        email = request.form['email']
        name = request.form['name']

        cur = mysql.connection.cursor()
        cur.execute("UPDATE user SET username=%s, email=%s, name=%s WHERE userid=%s",(username,email,name,userid))
        mysql.connection.commit()
        flash("Data berhasil di update")
        return redirect(url_for('pengguna'))
                          
    return render_template('pengguna.html',active_page='pengguna')

@app.route('/delete_pengguna/<int:userid>')
def delete_pengguna(userid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM user WHERE userid=%s", (userid,))
    mysql.connection.commit()
    flash("Data berhasil di hapus")
    return redirect(url_for('pengguna'))
                          
    return render_template('pengguna.html',active_page='pengguna')

@app.route('/recipe')
def recipe():
    if session.get('loggedin') and session.get('actor') == '1':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM recipe ORDER BY title ASC")
        tampilresep = cur.fetchall()
        cur.close()
        return render_template('recipe.html',active_page='recipe', dataresep=tampilresep)
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))
    
    

@app.route('/add_recipe', methods=('GET','POST'))
def add_recipe():
    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        steps = request.form['steps']
        url = request.form['url']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO recipe (title,ingredients,steps,url) VALUES (%s,%s,%s,%s)",(title,ingredients,steps,url))
        mysql.connection.commit()
        flash("Data berhasil di tambahkan")
        return redirect(url_for('recipe'))
                          
    return render_template('recipe_add.html',active_page='recipe')

@app.route('/delete_recipe/<int:id>')
def delete_recipe(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM recipe WHERE id=%s", (id,))
    mysql.connection.commit()
    flash("Data berhasil di hapus")
    return redirect(url_for('recipe'))

@app.route('/update_recipe/<int:id>', methods=['GET', 'POST'])
def update_recipe(id):
    if request.method == 'POST':
        
        title = request.form['title']
        ingredients = request.form['ingredients']
        steps = request.form['steps']
        url = request.form['url']

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE recipe SET title=%s, ingredients=%s, steps=%s, url=%s WHERE id=%s",
            (title, ingredients, steps, url, id)
        )
        mysql.connection.commit()
        flash("Data berhasil di update")
        return redirect(url_for('recipe'))  
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM recipe WHERE id=%s", (id,))
    row = cur.fetchone()  
    
    if row is None:
        flash("Recipe not found")
        return redirect(url_for('recipe'))  

    return render_template('recipe_update.html', active_page='recipe', row=row)



@app.route('/food')
def food():
     return render_template('food.html',active_page='food')

@app.route('/add_food')
def add_food():
                          
    return render_template('add_food.html',active_page='food')

@app.route('/article')
def article():
    if session.get('loggedin') and session.get('actor') == '1':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM article ORDER BY created ASC")
        tampilartikel = cur.fetchall()
        cur.close()
        
        return render_template('article.html',active_page='article', dataartikel=tampilartikel)
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))
    

@app.route('/add_article', methods=('GET', 'POST'))
def add_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO article (title, content, created, category) VALUES (%s, %s, NOW(), %s)",
            (title, content, category)
        )
        mysql.connection.commit()
        flash("Data berhasil ditambahkan")
        return redirect(url_for('article'))
                          
    return render_template('article_add.html',active_page='article')

@app.route('/update_article/<int:id>', methods=['GET', 'POST'])
def update_article(id):
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE article SET title=%s, content=%s, category=%s WHERE id=%s", (title, content, category, id))
        mysql.connection.commit()
        
        flash("Article updated successfully!")
        return redirect(url_for('article'))

    # For GET requests: Fetch the article to display in the form
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM article WHERE id=%s", (id,))
    row = cur.fetchone()
    
    return render_template('article_update.html',active_page='article', row=row)



@app.route('/delete_article/<int:id>')
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM article WHERE id=%s", (id,))
    mysql.connection.commit()
    flash("Data berhasil di hapus")
    return redirect(url_for('article'))


UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'upload' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['upload']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        
        return jsonify({'uploaded': 1, 'url': url_for('static', filename=f'uploads/{filename}', _external=True)})
    
    return jsonify({'error': 'File not allowed'})

if __name__ == '__main__':
    app.run(debug=True)