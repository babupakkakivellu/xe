from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import tempfile
import sqlite3
import pickle

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load the token.pickle file
with open('token.pickle', 'rb') as token:
    creds = pickle.load(token)

# Initialize Google Drive service
service = build('drive', 'v3', credentials=creds)

# Folder ID where files will be uploaded
FOLDER_ID = '1j83pj6sIL2mfNiWFqOYbb21vvNvlTwqd'

# Database setup
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            file_name TEXT NOT NULL,
            drive_link TEXT NOT NULL,
            pages_to_print TEXT,
            pages_color TEXT,
            special_instructions TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper function to parse pages input
def parse_pages(pages_input):
    """Parse the pages input into a list of integers."""
    pages = []
    try:
        for part in pages_input.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
    except Exception as e:
        flash(f"Invalid page format: {str(e)}")
        return []
    return sorted(set(pages))  # Remove duplicates and sort

# Home page
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

# Order form page
@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form data
        customer_name = request.form['customer_name']
        documents = request.files.getlist('documents')  # Multiple files
        pages_color = ', '.join(request.form.getlist('pages_color'))
        pages_to_print = request.form['pages_to_print']
        special_instructions = request.form['special_instructions']

        if not documents or all(doc.filename == '' for doc in documents):
            flash('No selected files')
            return redirect(request.url)

        # Parse pages to print
        parsed_pages = parse_pages(pages_to_print)
        if not parsed_pages:
            flash("Please enter valid page numbers.")
            return redirect(request.url)

        # Save and upload each file
        for document in documents:
            if document.filename == '':
                continue

            # Save the uploaded file temporarily using tempfile
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                filepath = temp_file.name  # Get the temporary file path
                document.save(filepath)  # Save the uploaded file to the temporary location

            # Upload the file to Google Drive
            try:
                file_metadata = {
                    'name': document.filename,
                    'parents': [FOLDER_ID]
                }
                media = MediaFileUpload(filepath, resumable=True)
                file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                drive_link = file.get('webViewLink')

                # Save order details to the database
                conn = sqlite3.connect('orders.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO orders (customer_name, file_name, drive_link, pages_to_print, pages_color, special_instructions)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_name, document.filename, drive_link, pages_to_print, pages_color, special_instructions))
                conn.commit()
                conn.close()

            except Exception as e:
                flash(f'Error uploading file: {str(e)}')
            finally:
                # Clean up the temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)

        flash('Files uploaded successfully!')
        return jsonify({'success': True})

    return render_template('index.html')

# Admin login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple hardcoded authentication
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

# Admin page to view orders
@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Fetch pending and completed orders from the database
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE status = "Pending" ORDER BY id DESC')
    pending_orders = c.fetchall()
    c.execute('SELECT * FROM orders WHERE status = "Completed" ORDER BY id DESC')
    completed_orders = c.fetchall()
    conn.close()

    return render_template('admin.html', pending_orders=pending_orders, completed_orders=completed_orders)

# Mark order as completed
@app.route('/mark_done/<int:order_id>', methods=['POST'])
def mark_done(order_id):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('UPDATE orders SET status = "Completed" WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Remove order
@app.route('/remove_order/<int:order_id>', methods=['POST'])
def remove_order(order_id):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Get port dynamically
    app.run(host="0.0.0.0", port=port, debug=True)  # Bind to 0.0.0.0
