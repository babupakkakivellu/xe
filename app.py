from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
import tempfile
import sqlite3
import pickle
import uuid
import mimetypes
import re  # For input validation

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load credentials and initialize Drive service
with open('token.pickle', 'rb') as token:
    creds = pickle.load(token)
service = build('drive', 'v3', credentials=creds)

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

# Input Validation
def validate_pages_input(pages_to_print):
    """
    Validates the pages_to_print input.
    Returns True if valid, False otherwise.
    """
    pattern = r'^[\d,\-\s]+$'  # Allow digits, commas, hyphens, and spaces only
    return bool(re.match(pattern, pages_to_print))

# Parse Pages Function
def parse_pages(pages_input):
    """
    Parses a string of page ranges (e.g., "1, 3-5") into a list of integers.
    Handles invalid inputs gracefully.
    """
    pages = []
    for part in pages_input.split(','):
        part = part.strip()
        if '-' in part:  # Handle ranges like "3-5"
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    pages.extend(range(start, end + 1))
                else:
                    print(f"Invalid range: {part}")
            except ValueError:
                print(f"Invalid range format: {part}")
        else:  # Handle single numbers like "1"
            try:
                pages.append(int(part))
            except ValueError:
                print(f"Invalid page number: {part}")
    return sorted(set(pages))  # Remove duplicates and sort the list

# Routes
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        documents = request.files.getlist('documents')
        pages_color = ', '.join(request.form.getlist('pages_color'))
        pages_to_print = request.form['pages_to_print']
        special_instructions = request.form['special_instructions']

        # Validate required fields
        if not customer_name:
            return jsonify({'success': False, 'message': 'Customer name is required.'}), 400

        if not documents or all(doc.filename == '' for doc in documents):
            return jsonify({'success': False, 'message': 'No selected files.'}), 400

        # Validate pages_to_print format
        if not validate_pages_input(pages_to_print):
            return jsonify({'success': False, 'message': 'Invalid input format for pages. Please use numbers, commas, and hyphens only.'}), 400

        # Parse pages
        parsed_pages = parse_pages(pages_to_print)
        if not parsed_pages:
            return jsonify({'success': False, 'message': 'Invalid page numbers.'}), 400

        # Process each document
        for document in documents:
            if document.filename == '':
                continue

            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, f"upload_{uuid.uuid4()}.tmp")

            try:
                document.save(filepath)

                # Determine MIME type
                mimetype, _ = mimetypes.guess_type(document.filename)
                if mimetype is None:
                    mimetype = 'application/octet-stream'

                file_metadata = {'name': document.filename, 'parents': [FOLDER_ID]}

                with open(filepath, 'rb') as fh:
                    media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
                    file = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()

                drive_link = file.get('webViewLink')

                # Save order details to the database
                conn = sqlite3.connect('orders.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO orders 
                    (customer_name, file_name, drive_link, pages_to_print, pages_color, special_instructions)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_name, document.filename, drive_link, pages_to_print, pages_color, special_instructions))
                conn.commit()
                conn.close()

            except Exception as e:
                print(f"Error: {str(e)}")
                return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

            finally:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Error deleting file: {e}")

        return jsonify({'success': True, 'message': 'Files uploaded successfully!'})

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
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute('UPDATE orders SET status = "Completed" WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error marking order as done: {str(e)}")
        return jsonify({'success': False}), 500

# Remove order
@app.route('/remove_order/<int:order_id>', methods=['POST'])
def remove_order(order_id):
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error removing order: {str(e)}")
        return jsonify({'success': False}), 500

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Get port dynamically
    app.run(host="0.0.0.0", port=port, debug=True)  # Bind to 0.0.0.0