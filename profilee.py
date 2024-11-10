from flask import Flask
app = Flask(__name__)

@app.route('/')
def profile():
    return "<h2>Profile</h2>"

if __name__ == '__main__':
    app.run()