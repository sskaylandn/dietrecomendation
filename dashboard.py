from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
def profile():
    return "<h2>profile</h2>"

@app.route('/recipe')
def recipe():
    return "<h2>recipe</h2>"

@app.route('/recomendation')
def recomendation():
    return "<h2>recomendation</h2>"

@app.route('/article')
def article():
     return render_template('article.html')

@app.route('/login')
def login():
     return render_template('login.html')

@app.route('/signup')
def signup():
     return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)