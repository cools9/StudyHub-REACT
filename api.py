from flask import Flask, jsonify, request, abort, make_response
from supabase import create_client, Client
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Supabase URL and API Key
url = "https://xbsywxlzzvjkfnurmoaj.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhic3l3eGx6enZqa2ZudXJtb2FqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjMzNjExODgsImV4cCI6MjAzODkzNzE4OH0.fskAVBTCjzBJl5gpr08dhmgAn5y-oRJhPjAWkFL5iQ4"  # Replace with your actual API key

# Initialize Supabase client
supabase: Client = create_client(url, key)

# JWT secret key
JWT_SECRET = os.urandom(24)  # You can replace this with a fixed secret in production
JWT_EXPIRATION_TIME_MINUTES = 30  # Token expiration time

def token_required(f):
    """Decorator to check for a valid JWT token in the request headers."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')  # Get the token from the cookie

        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.user = data['username']  # Store the username from the token in the request context
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(*args, **kwargs)

    return decorated

def generate_token(username):
    """Generate a JWT token for the given username."""
    expiration_time = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_TIME_MINUTES)
    token = jwt.encode({'username': username, 'exp': expiration_time}, JWT_SECRET, algorithm="HS256")
    return token

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Check if the user already exists
    response = supabase.table("users").select("*").eq('username', username).execute()
    if response.data:
        return jsonify({"message": "Username already exists, please log in."}), 400

    # Insert new user into Supabase
    response = supabase.table("users").insert({'username': username, 'password': password}).execute()
    if response.data:
        token = generate_token(username)
        resp = make_response(jsonify({"message": "User signed up successfully."}), 201)
        # Set the token as an HTTP-only cookie
        resp.set_cookie('token', token, httponly=True, secure=True, samesite='Strict')
        return resp
    else:
        error_message = response.error or "Error signing up"
        return jsonify({"error": error_message}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Check if the username and password match
    response = supabase.table("users").select("*").eq('username', username).eq('password', password).execute()

    if response.data:
        token = generate_token(username)
        resp = make_response(jsonify({"message": "Logged in successfully."}), 200)
        # Set the token as an HTTP-only cookie
        resp.set_cookie('token', token, httponly=True, secure=True, samesite='Strict')
        return resp
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({"message": "Logged out successfully."}), 200)
    # Clear the cookie by setting its expiration date in the past
    resp.set_cookie('token', '', expires=0, httponly=True, secure=True, samesite='Strict')
    return resp

@app.route('/api/add-notes', methods=['POST'])
@token_required
def add_notes():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    content = data.get('content')
    uploaded_by = request.user  # Get the currently logged-in user's username from the token

    # Insert new entry into Supabase
    response = supabase.table("uploads").insert({
        'title': title,
        'description': description,
        'content': content,
        'uploaded_by': uploaded_by
    }).execute()

    if response.data:
        return jsonify({"message": "Note added successfully."}), 201
    else:
        error_message = response.error or "Error adding entry"
        return jsonify({"error": error_message}), 500

@app.route('/api/content/<int:content_id>', methods=['GET'])
@token_required
def get_content(content_id):
    response = supabase.table("uploads").select("*").eq('id', content_id).execute()

    if response and response.data:
        content = response.data[0]
        return jsonify(content)
    else:
        return jsonify({"error": "Content not found"}), 404

@app.route('/api/my-posts', methods=['GET'])
@token_required
def my_posts():
    username = request.user  # Get the currently logged-in user's username from the token

    # Query the 'uploads' table for posts uploaded by the logged-in user
    response = supabase.table("uploads").select("*").eq('uploaded_by', username).execute()

    if response:
        data = response.data
    else:
        data = []

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
