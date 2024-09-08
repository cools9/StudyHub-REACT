from flask import Flask, render_template, request, redirect, url_for, abort, session, flash
from supabase import create_client, Client
import os
from functools import wraps

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)  # For session management

# Supabase URL and API Key
url = "https://xbsywxlzzvjkfnurmoaj.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhic3l3eGx6enZqa2ZudXJtb2FqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjMzNjExODgsImV4cCI6MjAzODkzNzE4OH0.fskAVBTCjzBJl5gpr08dhmgAn5y-oRJhPjAWkFL5iQ4"  # Replace with your actual API key

# Initialize Supabase client
supabase: Client = create_client(url, key)

# Custom login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def main():
    # Query the 'uploads' table
    response = supabase.table("uploads").select("*").execute()
    if response:
        data = response.data
    else:
        data = []

    return render_template('index.html', data=data)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the user already exists
        response = supabase.table("users").select("*").eq('username', username).execute()
        if response.data:
            # Redirect to login page if username already exists
            flash("Username already exists, please log in.")
            return redirect(url_for('login'))

        # Insert new user into Supabase
        response = supabase.table("users").insert({
            'username': username,
            'password': password
        }).execute()

        if response.data:
            # Set session and redirect to main
            session['username'] = username
            return redirect(url_for('main'))
        else:
            error_message = response.error or "Error signing up"
            return f"{error_message}", 500

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username and password match
        response = supabase.table("users").select("*").eq('username', username).eq('password', password).execute()

        if response.data:
            # Set session and redirect to main
            session['username'] = username
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/add-notes', methods=['GET', 'POST'])
@login_required
def add_notes():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content')
        uploaded_by = session.get('username')  # Get the currently logged-in user's username

        # Insert new entry into Supabase
        response = supabase.table("uploads").insert({
            'title': title,
            'description': description,
            'content': content,
            'uploaded_by': uploaded_by  # Add the username to the uploaded_by column
        }).execute()

        if response.data:
            return redirect(url_for('main'))
        else:
            error_message = response.error or "Error adding entry"
            return f"{error_message}", 500

    return render_template('add-notes.html')

@app.route('/content/<int:content_id>')
@login_required
def content(content_id):
    # Query the 'uploads' table for a specific content ID
    response = supabase.table("uploads").select("*").eq('id', content_id).execute()

    if response and response.data:
        content = response.data[0]  # Assuming there's only one result
    else:
        abort(404)  # If not found, return a 404 error

    return render_template('content.html', content=content)

@app.route('/my-posts')
@login_required
def my_posts():
    username = session.get('username')  # Get the currently logged-in user's username

    # Query the 'uploads' table for posts uploaded by the logged-in user
    response = supabase.table("uploads").select("*").eq('uploaded_by', username).execute()

    if response:
        data = response.data
    else:
        data = []

    return render_template('my_posts.html', data=data)

@app.route('/session')
@login_required
def session_info():
    return render_template('session.html')

@app.route('/create-session')
@login_required
def session_creat():
    return render_template('create_session.html')

@app.route('/join-session')
@login_required
def session_join():
    return render_template('join_session.html')

if __name__ == '__main__':
    app.run(debug=True)
