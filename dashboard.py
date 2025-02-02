from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_ckeditor import CKEditor
from datetime import datetime
from recomendation import calculate_bmr, adjust_calories_for_goal, calculate_tdee, recommend_balanced_meals  
import os
import json
import pandas as pd
import pickle
import joblib
from joblib import load

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

rf_model = joblib.load('./rf_model.joblib'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user_dashboard')
def user_dashboard():
    if session.get('loggedin') and session.get('actor') == '2': 
        userid = session.get('userid')  

        cur = mysql.connection.cursor()
        cur.execute("SELECT height, gender, age, goal, activity FROM usercharacteristics WHERE userid = %s", (userid,))
        user_data = cur.fetchone()  
        cur.execute(" SELECT weight FROM tracker WHERE userid = %s ORDER BY datesubmit DESC LIMIT 1", (userid,))
        latest_weight = cur.fetchone()
        cur.close()

        no_data_message = ""
        add_userchar = ""

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT datesubmit, weight FROM tracker WHERE userid = %s ORDER BY datesubmit ASC", [userid])
        weightdata = cursor.fetchall()

        #grafik
        labels = [row[0].strftime('%d-%m-%Y') for row in weightdata]  
        weight_values = [row[1] for row in weightdata]  

        data_exists = bool(user_data)
        data_dict = {}

        if data_exists:
            height = user_data[0]
            weight = latest_weight[0]
            gender = user_data[1]
            age = user_data[2]
            goal = user_data[3]
            activity = user_data[4]  

            height_in_meters = height / 100  
            bmi = weight / (height_in_meters ** 2) if height_in_meters > 0 else "-"

            if gender == 'pria':
                bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            elif gender == 'wanita':
                bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
            else:
                bmr = "-"

            activity_multipliers = {
                'sedentary': 1.3,
                'lowactive': 1.5,
                'active': 1.7,
                'veryactive': 2
            }

            # multiplier berdasarkan aktivitas 
            multiplier = activity_multipliers.get(activity.lower(), 1)  
            tdee = bmr * multiplier if isinstance(bmr, (int, float)) else "-"

            # selisih berat badan 
            if weightdata:
                oldest_date = weightdata[0][0].strftime('%d-%m-%Y')  
                latest_date = weightdata[-1][0].strftime('%d-%m-%Y')  
                weight_difference = round(weightdata[-1][1] - weightdata[0][1], 2)  
            else:
                oldest_date = latest_date = weight_difference = None

            # data pengguna
            data_dict = {
                "height": height or "-",
                "weight": weight or "-",
                "bmi": round(bmi, 2) if isinstance(bmi, (int, float)) else "-",
                "tdee": round(tdee, 2) if isinstance(tdee, (int, float)) else "-",
                "bmr": round(bmr, 2) if isinstance(bmr, (int, float)) else "-",
                "goal": goal or "-",
                "activity": activity or "-",
            }

            
            if weightdata:
                data_dict["weight_difference"] = weight_difference
                data_dict["oldest_date"] = oldest_date
                data_dict["latest_date"] = latest_date

        else:
           
            no_data_message = "Belum ada data tersedia saat ini. Silakan tambahkan data Anda melalui tombol di bawah ini:"
            add_userchar = url_for('add_userchar')  

        return render_template('user_dashboard.html', 
                             data=data_dict, 
                             data_exists=data_exists, 
                             no_data_message=no_data_message, 
                             add_userchar=add_userchar, 
                             labels=labels, 
                             weight_values=weight_values, latest_weight=latest_weight)
    
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



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    userid = session.get('userid')
    if not userid:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))  
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT * FROM user WHERE userid = %s", [userid])
    user_data = cursor.fetchone()
    
    cursor.execute("SELECT * FROM usercharacteristics WHERE userid = %s", [userid])
    characteristic_data = cursor.fetchone()
    
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        height = request.form.get('height')
        gender = request.form.get('gender')
        age = request.form.get('age')
        goal = request.form.get('goal')
        activity = request.form.get('activity')

        cursor.execute("SELECT COUNT(*) FROM user WHERE username = %s AND userid != %s", (username, userid))
        result = cursor.fetchone()
        
        if result[0] > 0:  
            flash('Username sudah digunakan oleh pengguna lain. Silakan pilih username lain.', 'danger')
        else:
            cursor.execute("UPDATE user SET username = %s, name = %s WHERE userid = %s", (username, name, userid))

            cursor.execute("""UPDATE usercharacteristics SET height = %s, gender = %s, age = %s, goal = %s, activity = %s 
                              WHERE userid = %s""", (height, gender, age, goal, activity, userid))
            
            mysql.connection.commit()  
            flash('Profile updated successfully!', 'success')  
            return redirect(url_for('profile'))  

    return render_template('profile.html', user=user_data, user_characteristics=characteristic_data)

@app.route('/admprofile', methods=['GET', 'POST'])
def admprofile():
    userid = session.get('userid')
    if not userid:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))  
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT * FROM user WHERE userid = %s", [userid])
    user_data = cursor.fetchone()
    
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        
        cursor.execute("SELECT COUNT(*) FROM user WHERE username = %s AND userid != %s", (username, userid))
        result = cursor.fetchone()
        
        if result[0] > 0:  
            flash('Username sudah digunakan oleh pengguna lain. Silakan pilih username lain.', 'danger')
        else:
            cursor.execute("UPDATE user SET username = %s, name = %s WHERE userid = %s", (username, name, userid))

            
            mysql.connection.commit()  
            flash('Profile updated successfully!', 'success')  
            return redirect(url_for('admprofile'))  

    return render_template('admprofile.html', user=user_data, )



@app.route('/add_userchar', methods=['GET', 'POST'])
def add_userchar():
    if request.method == 'POST':
        height = request.form['height']
        weight = request.form['weight']
        gender = request.form['gender']
        age = request.form['age']
        goal = request.form['goal']
        activity = request.form['activity']
        
       
        datesubmit = datetime.now().date()  
        userid = session.get('userid')
        if userid is None:
            flash("Anda harus login terlebih dahulu")
            return redirect(url_for('login'))

        cur = mysql.connection.cursor()
        
        cur.execute("""
            INSERT INTO usercharacteristics (userid, height, weight, gender, age, goal, activity)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (userid, height, weight, gender, age, goal, activity))
        
        cur.execute("""
            INSERT INTO tracker (userid, weight,datesubmit)
            VALUES (%s, %s, %s)
        """, (userid, weight,  datesubmit))

        mysql.connection.commit()
        cur.close()
        flash("Data berhasil ditambahkan ke kedua tabel")
        return redirect(url_for('user_dashboard'))

    return render_template('userchar_add.html')


@app.route('/plandiet', methods=['GET', 'POST'])
def plandiet():
    filtered_data = pd.read_csv('tkpi_filtered.csv')
    userid = session.get('userid')  

    if not userid:
        return redirect(url_for('login'))  

    user_data = get_user_data_by_id(userid)

    if user_data:
            gender = user_data['gender']
            age = user_data['age']
            weight = user_data['weight']
            height = user_data['height']
            activity = user_data['activity']
            goal = user_data['goal']
    else:
            gender, age, weight, height, activity, goal = '', '', '', '', '', ''


    page = request.args.get('page', 1, type=int) 
    per_page = 5  
    active_plan = get_active_diet_plan(userid)
    inactive_plans, total_data, total_pages = get_inactive_diet_plans_by_user(userid, page, per_page)

    meal_dict = {
        'breakfast': {},
        'lunch': {},
        'dinner': {},
        'snacks': {}
    }

    if inactive_plans:
        for plan in inactive_plans:
            plan_id = plan[0]  
            
            # Mengambil data sarapan
            breakfast_data = plan[2] 
            if breakfast_data:
                try:
                    meal_dict['breakfast'][plan_id] = json.loads(breakfast_data)
                except json.JSONDecodeError:
                    meal_dict['breakfast'][plan_id] = [] 
            else:
                meal_dict['breakfast'][plan_id] = []  
            
            # Mengambil data makan siang
            lunch_data = plan[3]  
            if lunch_data:
                try:
                    meal_dict['lunch'][plan_id] = json.loads(lunch_data)
                except json.JSONDecodeError:
                    meal_dict['lunch'][plan_id] = []  
            else:
                meal_dict['lunch'][plan_id] = []  
            
            # Mengambil data makan malam
            dinner_data = plan[4] 
            if dinner_data:
                try:
                    meal_dict['dinner'][plan_id] = json.loads(dinner_data)
                except json.JSONDecodeError:
                    meal_dict['dinner'][plan_id] = []  
            else:
                meal_dict['dinner'][plan_id] = []  
            
            # Mengambil data camilan
            snacks_data = plan[5] 
            if snacks_data:
                try:
                    meal_dict['snacks'][plan_id] = json.loads(snacks_data)
                except json.JSONDecodeError:
                    meal_dict['snacks'][plan_id] = [] 
            else:
                meal_dict['snacks'][plan_id] = []  
    else:
        meal_dict = {
            'breakfast': {},
            'lunch': {},
            'dinner': {},
            'snacks': {}
        }

    if active_plan:
        bmr = active_plan['bmr']
        tdee = active_plan['tdee']
        adjustedbmr = active_plan['adjustedbmr']
        breakfast = pd.read_json(active_plan['breakfast'])
        lunch = pd.read_json(active_plan['lunch'])
        dinner = pd.read_json(active_plan['dinner'])
        snacks = pd.read_json(active_plan['snacks'])
        goal = active_plan['goal']
    else:
        bmr = tdee = adjustedbmr = breakfast = lunch = dinner = snacks = goal = None

    if request.method == 'POST':
        # Get data from the form that is submitted
        gender = request.form['gender']
        age = int(request.form['age'])
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        activity = request.form['activity']
        goal = request.form['goal']

        user_input = {
            'gender': gender,
            'age': age,
            'weight': weight,
            'height': height,
            'activity': activity,
            'goal': goal
        }

        # Calculate BMR and TDEE
        bmr = calculate_bmr(user_input['gender'], user_input['age'], user_input['weight'], user_input['height'])
        tdee = calculate_tdee(bmr, user_input['activity'])
        adjustedbmr = adjust_calories_for_goal(tdee, bmr, user_input['goal'])


        bmr = bmr or 0
        tdee = tdee or 0
        adjustedbmr = adjustedbmr or 0

        # meal recommendations
        breakfast, lunch, dinner, snacks = recommend_balanced_meals(tdee, bmr, goal, filtered_data)


        breakfast = breakfast[['NAMA BAHAN', 'ENERGI', 'PROTEIN', 'KH', 'SERAT']]
        lunch = lunch[['NAMA BAHAN', 'ENERGI', 'PROTEIN', 'KH', 'SERAT']]
        dinner = dinner[['NAMA BAHAN', 'ENERGI', 'PROTEIN', 'KH', 'SERAT']]
        snacks = snacks[['NAMA BAHAN', 'ENERGI', 'PROTEIN', 'KH', 'SERAT']]

       # Extract onlyNAMA BAHAN
        breakfast_names = breakfast['NAMA BAHAN'].tolist()
        lunch_names = lunch['NAMA BAHAN'].tolist()
        dinner_names = dinner['NAMA BAHAN'].tolist()
        snack_names = snacks['NAMA BAHAN'].tolist()

        deactivate_old_plans(userid)

        # Store names as JSON
        insert_new_plandiet(userid, json.dumps(breakfast_names), json.dumps(lunch_names), json.dumps(dinner_names), json.dumps(snack_names), bmr, tdee, adjustedbmr)


        # render the template
        result = {
            'bmr': bmr,
            'tdee': tdee,
            'goal': user_input['goal'],
            'adjustedbmr': adjustedbmr,
            'breakfast': breakfast,
            'lunch': lunch,
            'dinner': dinner,
            'snacks': snacks,
        }

        return render_template('plandiet.html', active_page='plandiet', result=result, inactive_plans=inactive_plans, meal_dict=meal_dict, total_pages=total_pages, page=page)

    return render_template('plandiet.html', active_page='plandiet',  gender=gender, age=age, weight=weight, height=height, activity=activity, goal=goal, bmr=bmr, tdee=tdee, adjustedbmr=adjustedbmr, breakfast=breakfast, lunch=lunch, dinner=dinner, snacks=snacks, inactive_plans=inactive_plans, meal_dict=meal_dict, total_pages=total_pages, page=page )



def insert_new_plandiet(userid, breakfast, lunch, dinner, snacks, bmr, tdee, adjustedbmr):
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = """
    INSERT INTO dietplan (userid, breakfast, lunch, dinner, snacks, bmr, tdee, adjustedbmr, created, updated, isActive)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (userid, breakfast, lunch, dinner, snacks, bmr, tdee, adjustedbmr, current_time, current_time, 1)

    execute_query(query, params)


def deactivate_old_plans(userid):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
    UPDATE dietplan
    SET isActive = 0, updated = %s
    WHERE userid = %s AND isActive = 1
    """
    
    execute_query(query, (current_time, userid))

def get_active_diet_plan(userid):
    query = """
    SELECT bmr, tdee, adjustedbmr, breakfast, lunch, dinner, snacks
    FROM dietplan
    WHERE userid = %s AND isActive = 1
    """
    cursor = execute_query(query, (userid,))
    
    if cursor:
        result = cursor.fetchone()
        return result
    else:
        return None
    
def get_inactive_diet_plans_by_user(userid, page, per_page):
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM dietplan WHERE userid = %s", (userid,))
    total_data = cur.fetchone()[0]

    total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)

    
    offset = (page - 1) * per_page

    cur.execute("SELECT * FROM dietplan WHERE userid = %s ORDER BY created ASC LIMIT %s OFFSET %s", (userid, per_page, offset))
    tampilplan = cur.fetchall()

    cur.close()

    return tampilplan, total_data, total_pages 

def execute_query(query, params):
  
    cursor = mysql.connection.cursor()
    cursor.execute(query, params)
    mysql.connection.commit()
    cursor.close()

# Function to fetch user data 
def get_user_data_by_id(user_id):
    cursor = mysql.connection.cursor()
    query = "SELECT gender, age, weight, height, activity, goal FROM usercharacteristics WHERE userid = %s"
    cursor.execute(query, (user_id,))
    user_data = cursor.fetchone()  
    cursor.close()

    if user_data:
      
        return {
            'gender': user_data[0],  
            'age': user_data[1],     
            'weight': user_data[2],   
            'height': user_data[3],  
            'activity': user_data[4], 
            'goal': user_data[5]     
        }
    else:
        return None


# API endpoint untuk menerima input dari pengguna
@app.route('/api/recomendation', methods=['POST'])
def api_recomendation():
    # Mengambil data JSON yang dikirim dari client (misal melalui Postman atau fetch API)
    data = request.get_json()
    
    user_input = data.get('user_input')  # Ambil input data pengguna
    userid = session.get('userid')  # Dapatkan user_id dari session

    if not user_input or not userid:
        return jsonify({"error": "Missing input or user ID"}), 400

    # Panggil fungsi dari recommendation.py
    result = recomendation.process_recommendation(user_input, userid)

    return jsonify({"recommendation": result})


    

@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    # Cek apakah ada userid di session
    userid = session.get('userid')
    if not userid:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))  # Jika tidak ada session userid, arahkan ke halaman login

    cursor = mysql.connection.cursor()

    # Ambil data untuk grafik berat badan
    cursor.execute("SELECT datesubmit, weight FROM tracker WHERE userid = %s ORDER BY datesubmit ASC", [userid])
    weightdata = cursor.fetchall()

    # Siapkan data untuk grafik berat badan
    labels = [row[0].strftime('%d-%m-%Y') for row in weightdata]   # Mengambil tanggal dan memformatnya
    weight_values = [row[1] for row in weightdata]  # Mengambil berat badan dari data

    # Ambil data untuk grafik lingkar tubuh (belly, waist, thigh, arm)
    cursor.execute("""
        SELECT datesubmit, belly, waist, thigh, arm 
        FROM tracker 
        WHERE userid = %s 
        ORDER BY datesubmit ASC
    """, [userid])
    body_data = cursor.fetchall()

    # Siapkan data untuk grafik lingkar tubuh
    belly_values = [row[1] for row in body_data]
    waist_values = [row[2] for row in body_data]
    thigh_values = [row[3] for row in body_data]
    arm_values = [row[4] for row in body_data]

    # Menghitung selisih antara data terbaru dan terlama
    if weightdata:
        weight_difference = round(weight_values[0] - weight_values[-1], 2)
        belly_difference = round(belly_values[0] - belly_values[-1], 2)
        waist_difference = round(waist_values[0] - waist_values[-1], 2)
        thigh_difference = round(thigh_values[0] - thigh_values[-1], 2)
        arm_difference = round(arm_values[0] - arm_values[-1], 2)
    else:
        weight_difference = belly_difference = waist_difference = thigh_difference = arm_difference = None

    # Mengambil nomor halaman dari parameter query atau default ke 1
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Jumlah data per halaman
    offset = (page - 1) * per_page  # Tentukan data awal untuk halaman saat ini

    # Ambil data dengan paginasi dari tabel tracker berdasarkan userid
    cursor.execute("SELECT * FROM tracker WHERE userid = %s ORDER BY datesubmit DESC LIMIT %s OFFSET %s", (userid, per_page, offset))
    tracker_data = cursor.fetchall()

    # Menghitung total data untuk menentukan jumlah halaman
    cursor.execute("SELECT COUNT(*) FROM tracker WHERE userid = %s", [userid])
    total_data = cursor.fetchone()[0]
    total_pages = (total_data + per_page - 1) // per_page  # Pembulatan ke atas untuk jumlah halaman

    # Menangani POST request untuk menambah data baru
    if request.method == 'POST':
        datesubmit = request.form.get('datesubmit')
        
        # Cek apakah sudah ada data dengan tanggal yang sama di database
        cursor.execute("SELECT * FROM tracker WHERE userid = %s AND datesubmit = %s", [userid, datesubmit])
        existing_data = cursor.fetchone()

        if existing_data:
            flash(f"Data untuk tanggal {datesubmit} sudah tersedia.", 'danger')
            return redirect(url_for('tracker'))  # Mengarahkan kembali ke halaman tracker

        # Jika tidak ada data untuk tanggal tersebut, simpan data baru
        weight = request.form.get('weight')
        belly = request.form.get('belly')
        waist = request.form.get('waist')
        thigh = request.form.get('thigh')
        arm = request.form.get('arm')

        # Insert data baru ke dalam tabel
        cursor.execute(""" 
            INSERT INTO tracker (userid, weight, belly, waist, thigh, arm, datesubmit)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (userid, weight, belly, waist, thigh, arm, datesubmit))

        mysql.connection.commit()  # Commit perubahan ke database
        flash('Data tracker berhasil diperbarui!', 'success')  # Flash pesan sukses
        return redirect(url_for('tracker'))  # Redirect kembali ke halaman tracker

    # Jika tidak ada POST request, hanya tampilkan data
    return render_template(
        'tracker.html', 
        active_page='tracker', 
        tracker_data=tracker_data, 
        page=page, 
        total_pages=total_pages, 
        labels=labels, 
        weight_values=weight_values, 
        belly_values=belly_values, 
        waist_values=waist_values, 
        thigh_values=thigh_values, 
        arm_values=arm_values,
        weight_difference=weight_difference,
        belly_difference=belly_difference,
        waist_difference=waist_difference,
        thigh_difference=thigh_difference,
        arm_difference=arm_difference
    )



@app.route('/uarticle')
def uarticle():
    if session.get('loggedin') and session.get('actor') == '2':
        
        search = request.args.get('search', '')  
        category = request.args.get('category', '')  
        page = request.args.get('page', 1, type=int)  
        per_page = 6  

        cur = mysql.connection.cursor()

        query = "SELECT * FROM article WHERE 1=1"
        params = []

        if search:
            query += " AND (title LIKE %s OR content LIKE %s OR author LIKE %s OR category LIKE %s)"
            search_pattern = '%' + search + '%'
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY created ASC LIMIT %s OFFSET %s"
        params.append(per_page)
        params.append((page - 1) * per_page)

        cur.execute(query, tuple(params))
        tampilartikel = cur.fetchall()

        count_query = "SELECT COUNT(*) FROM article WHERE 1=1"
        count_params = []

        if search:
            count_query += " AND (title LIKE %s OR content LIKE %s OR author LIKE %s OR category LIKE %s)"
            count_params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

        if category:
            count_query += " AND category = %s"
            count_params.append(category)

        cur.execute(count_query, tuple(count_params))
        total_data = cur.fetchone()[0]

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)

        cur.close()

        cur = mysql.connection.cursor()
        cur.execute("""SELECT category, COUNT(*) as count FROM article GROUP BY category""")
        kategori_count = cur.fetchall()
        cur.close()

        jumlahkategori = {row[0]: row[1] for row in kategori_count}
        
        dataartikel = []
        for row in tampilartikel:
            first_sentence = row[2].split('.')[0] + '.' if '.' in row[2] else row[2]
            dataartikel.append({
                "id": row[0],
                "title": row[1],
                "first_sentence": first_sentence,
                "created": row[3],
                "author": row[5]
            })

        return render_template(
            'uarticle.html',
            active_page='article',
            dataartikel=dataartikel,
            jumlahkategori=jumlahkategori,
            search=search,
            category=category,
            page=page,
            total_pages=total_pages
        )
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))


    
@app.route('/detail_article/<int:id>')
def detail_article(id):
    if session.get('loggedin') and session.get('actor') == '2':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM article WHERE id = %s", (id,))
        tampilartikel = cur.fetchone()
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM article 
            GROUP BY category
        """)
        kategori_count = cur.fetchall()
        
        cur.close()
        jumlahkategori = {row[0]: row[1] for row in kategori_count}
        
        
        if tampilartikel:
            return render_template('uarticle_detail.html', active_page='uarticle',  article=tampilartikel, jumlahkategori=jumlahkategori)
        else:
            flash('Artikel tidak ditemukan.', 'warning')
            return redirect(url_for('uarticle'))
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))

@app.route('/tarticle')
def tarticle():
    
        # Ambil parameter pencarian dan kategori dari query string
        search = request.args.get('search', '')  # Jika tidak ada pencarian, defaultnya kosong
        category = request.args.get('category', '')  # Ambil kategori dari URL
        page = request.args.get('page', 1, type=int)  # Ambil nomor halaman, default ke halaman 1
        per_page = 10  # Jumlah artikel per halaman

        # Mulai membangun query untuk filter berdasarkan title, author, category
        cur = mysql.connection.cursor()

        query = "SELECT * FROM article WHERE 1=1"
        params = []

        # Filter berdasarkan pencarian
        if search:
            query += " AND (title LIKE %s OR content LIKE %s OR author LIKE %s OR category LIKE %s)"
            search_pattern = '%' + search + '%'
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

        # Filter berdasarkan kategori (jika ada)
        if category:
            query += " AND category = %s"
            params.append(category)

        # Pagination (LIMIT dan OFFSET)
        query += " ORDER BY created ASC LIMIT %s OFFSET %s"
        params.append(per_page)
        params.append((page - 1) * per_page)

        # Eksekusi query dengan parameter pencarian dan kategori
        cur.execute(query, tuple(params))
        tampilartikel = cur.fetchall()

        # Ambil jumlah total artikel berdasarkan filter pencarian dan kategori
        count_query = "SELECT COUNT(*) FROM article WHERE 1=1"
        count_params = []

        # Filter pencarian
        if search:
            count_query += " AND (title LIKE %s OR content LIKE %s OR author LIKE %s OR category LIKE %s)"
            count_params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

        # Filter kategori
        if category:
            count_query += " AND category = %s"
            count_params.append(category)

        cur.execute(count_query, tuple(count_params))
        total_data = cur.fetchone()[0]

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)

        cur.close()

        # Mengambil kategori artikel untuk sidebar
        cur = mysql.connection.cursor()
        cur.execute("""SELECT category, COUNT(*) as count FROM article GROUP BY category""")
        kategori_count = cur.fetchall()
        cur.close()

        # Mengubah kategori_count menjadi dictionary
        jumlahkategori = {row[0]: row[1] for row in kategori_count}
        
        # Membuat daftar artikel dengan potongan kalimat pertama
        dataartikel = []
        for row in tampilartikel:
            first_sentence = row[2].split('.')[0] + '.' if '.' in row[2] else row[2]
            dataartikel.append({
                "id": row[0],
                "title": row[1],
                "first_sentence": first_sentence,
                "created": row[3],
                "author": row[5]
            })

        return render_template(
            'tarticle.html',
            active_page='tarticle',
            dataartikel=dataartikel,
            jumlahkategori=jumlahkategori,
            search=search,
            category=category,
            page=page,
            total_pages=total_pages
        )
   

    
@app.route('/tdetail_article/<int:id>')
def tdetail_article(id):
   
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM article WHERE id = %s", (id,))
        tampilartikel = cur.fetchone()
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM article 
            GROUP BY category
        """)
        kategori_count = cur.fetchall()
        
        cur.close()
        jumlahkategori = {row[0]: row[1] for row in kategori_count}
        
        
        if tampilartikel:
            return render_template('tarticle_detail.html', active_page='tarticle',  article=tampilartikel, jumlahkategori=jumlahkategori)
        else:
            flash('Artikel tidak ditemukan.', 'warning')
            return redirect(url_for('tarticle'))
    

@app.route('/urecipe')
def urecipe():
    if session.get('loggedin') and session.get('actor') == '2':
        page = request.args.get('page', 1, type=int)
        per_page = 15 

        search_query = request.args.get('search', '') 

        cur = mysql.connection.cursor()

        if search_query:
            cur.execute("SELECT COUNT(*) FROM recipe WHERE title LIKE %s", ('%' + search_query + '%',))
        else:
            cur.execute("SELECT COUNT(*) FROM recipe")
        total_data = cur.fetchone()[0]

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)

        offset = (page - 1) * per_page

        if search_query:
            cur.execute("SELECT * FROM recipe WHERE title LIKE %s ORDER BY title ASC LIMIT %s OFFSET %s", ('%' + search_query + '%', per_page, offset))
        else:
            cur.execute("SELECT * FROM recipe ORDER BY title ASC LIMIT %s OFFSET %s", (per_page, offset))

        tampilresep = cur.fetchall()

        cur.close()

        return render_template(
            'urecipe.html',
            active_page='urecipe',
            dataresep=tampilresep,
            page=page,
            total_pages=total_pages,
            search=search_query  
        )
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))

    
@app.route('/detail_recipe/<int:id>')
def detail_recipe(id):
    if session.get('loggedin') and session.get('actor') == '2':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM recipe WHERE id = %s", (id,))
        resep_detail = cur.fetchone()
        cur.close()

        if resep_detail:
            return render_template('urecipe_detail.html', active_page='urecipe', resep=resep_detail)
        else:
            flash('Resep tidak ditemukan.', 'warning')
            return redirect(url_for('urecipe'))
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))



@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']  
        password = request.form['password']

        cursor = mysql.connection.cursor()

        cursor.execute('SELECT * FROM user WHERE email=%s OR username=%s', (email_or_username, email_or_username))
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
            elif session['actor'] == '1':  
                return redirect(url_for('admin_dashboard'))
    
    return render_template('login.html')


@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']
        actor = request.form['actor']

        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok', 'danger')
            return render_template('signup.html')
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


@app.route('/pengguna')
def pengguna():
    if session.get('loggedin') and session.get('actor') == '1':
        page = request.args.get('page', 1, type=int)
        per_page = 10  
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM user")
        total_data = cur.fetchone()[0]
        cur.close()

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)
        offset = (page - 1) * per_page
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user ORDER BY actor ASC LIMIT %s OFFSET %s", (per_page, offset))
        tampilpengguna = cur.fetchall()
        cur.close()
        return render_template('pengguna.html',active_page='pengguna',datapengguna=tampilpengguna, total_pages=total_pages,page=page)
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
        page = request.args.get('page', 1, type=int)
        per_page = 10 
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM recipe")
        total_data = cur.fetchone()[0]
        cur.close()

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)
        offset = (page - 1) * per_page
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM recipe ORDER BY title ASC LIMIT %s OFFSET %s", (per_page, offset))
        tampilresep = cur.fetchall()
        cur.close()

        return render_template('recipe.html', active_page='recipe',  dataresep=tampilresep,total_pages=total_pages, page=page)
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
        flash('Data berhasil ditambah.', 'success')
        return redirect(url_for('recipe'))
                          
    return render_template('recipe_add.html',active_page='recipe')

@app.route('/delete_recipe/<int:id>')
def delete_recipe(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM recipe WHERE id=%s", (id,))
    mysql.connection.commit()
    flash('Data berhasil di hapus.', 'danger')
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


@app.route('/article')
def article():
    if session.get('loggedin') and session.get('actor') == '1':
        page = request.args.get('page', 1, type=int)
        per_page = 10  
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM article")
        total_data = cur.fetchone()[0]
        cur.close()

        total_pages = (total_data // per_page) + (1 if total_data % per_page > 0 else 0)

        offset = (page - 1) * per_page

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM article ORDER BY created ASC LIMIT %s OFFSET %s", (per_page, offset))
        tampilartikel = cur.fetchall()
        cur.close()

        return render_template('article.html',active_page='article',dataartikel=tampilartikel,total_pages=total_pages,page=page)
    else:
        flash('Akses Ditolak. Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('login'))


@app.route('/add_article', methods=('GET', 'POST'))
def add_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        author = request.form['author']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO article (title, content, created, category, author) VALUES (%s, %s, NOW(), %s, %s)",
            (title, content, category,author)
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

@app.template_filter('from_json')
def from_json_filter(json_str):
    return json.loads(json_str)

# Register the filter
app.jinja_env.filters['from_json'] = from_json_filter

def is_dataframe(value):
    return isinstance(value, pd.DataFrame)

# Register the filter with Jinja2
app.jinja_env.filters['is_dataframe'] = is_dataframe

if __name__ == '__main__':
    app.run(debug=True)