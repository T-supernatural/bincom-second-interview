# app.py
from flask import Flask, render_template, request
import sqlite3
import os  # Import os module to check for file existence

app = Flask(__name__)

DATABASE_FILE = 'elections.db'  # Define your new database file name
SQL_SCRIPT_FILE = 'bincom_test.sql'  # The name of the provided SQL script

# --- Database Initialization Function ---


def init_db():
    # Only run this if the database file doesn't exist
    if not os.path.exists(DATABASE_FILE):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        print(f"Creating new database: {DATABASE_FILE} from {SQL_SCRIPT_FILE}")
        with open(SQL_SCRIPT_FILE, 'r') as f:
            sql_script = f.read()
            # Execute all commands from the SQL script
            cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    else:
        print(
            f"Database {DATABASE_FILE} already exists. Skipping initialization.")


# --- Database Connection Function (UPDATED to use new DB name) ---
def get_db_connection():
    # Connect to the newly created database file
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Route for Question 1 (Remains the same) ---


@app.route('/', methods=('GET', 'POST'))
def q1_polling_unit_results():
    conn = get_db_connection()
    polling_units = conn.execute(
        'SELECT uniqueid, polling_unit_name FROM polling_unit').fetchall()
    conn.close()

    selected_polling_unit_id = None
    results = None
    polling_unit_name = "No Polling Unit Selected"

    if request.method == 'POST':
        selected_polling_unit_id = request.form.get('polling_unit_id')
        if selected_polling_unit_id:
            conn = get_db_connection()
            # Fetch results for the selected polling unit
            results = conn.execute(
                'SELECT party_abbreviation, party_score FROM announced_pu_results WHERE polling_unit_uniqueid = ?',
                (selected_polling_unit_id,)
            ).fetchall()

            # Also fetch the name of the selected polling unit for display
            pu_info = conn.execute(
                'SELECT polling_unit_name FROM polling_unit WHERE uniqueid = ?',
                (selected_polling_unit_id,)
            ).fetchone()
            if pu_info:
                polling_unit_name = pu_info['polling_unit_name']
            conn.close()

    return render_template(
        'q1_polling_unit_selection.html',
        polling_units=polling_units,
        results=results,
        selected_polling_unit_id=selected_polling_unit_id,
        polling_unit_name=polling_unit_name
    )


# --- Route for Question 2 (NEWLY ADDED) ---
@app.route('/q2_lga_results', methods=['GET', 'POST'])
def q2_lga_results():
    conn = get_db_connection()
    lgas = conn.execute('SELECT lga_id, lga_name FROM lga').fetchall()
    results = None
    selected_lga_id = None
    selected_lga_name = None

    if request.method == 'POST':
        selected_lga_id = request.form.get('lga_id')
        if selected_lga_id:
            # Get the LGA name for display
            lga_row = conn.execute(
                'SELECT lga_name FROM lga WHERE lga_id = ?', (selected_lga_id,)).fetchone()
            selected_lga_name = lga_row['lga_name'] if lga_row else None
            # Aggregate total votes per party for the selected LGA
            results = conn.execute('''
                SELECT apr.party_abbreviation, SUM(apr.party_score) as total_score
                FROM announced_pu_results apr
                JOIN polling_unit pu ON apr.polling_unit_uniqueid = pu.uniqueid
                WHERE pu.lga_id = ?
                GROUP BY apr.party_abbreviation
                ORDER BY total_score DESC
            ''', (selected_lga_id,)).fetchall()
    conn.close()
    return render_template(
        'q2_lga_results.html',
        lgas=lgas,
        results=results,
        selected_lga_id=selected_lga_id,
        selected_lga_name=selected_lga_name
    )

# --- Route for Question 3 (NEWLY ADDED) ---


@app.route('/q3_store_results', methods=['GET', 'POST'])
def q3_store_results():
    conn = get_db_connection()
    polling_units = conn.execute(
        'SELECT uniqueid, polling_unit_name FROM polling_unit').fetchall()
    parties = conn.execute('SELECT partyid, partyname FROM party').fetchall()
    message = None
    success = False
    form_data = {'polling_unit_id': '', 'party_abbreviation': '',
                 'party_score': '', 'entered_by_user': ''}

    if request.method == 'POST':
        form_data['polling_unit_id'] = request.form.get(
            'polling_unit_id', '').strip()
        form_data['party_abbreviation'] = request.form.get(
            'party_abbreviation', '').strip()
        form_data['party_score'] = request.form.get('party_score', '').strip()
        form_data['entered_by_user'] = request.form.get(
            'entered_by_user', '').strip()
        # Validation
        if not all(form_data.values()):
            message = 'All fields are required.'
        elif not form_data['party_score'].isdigit():
            message = 'Party score must be a number.'
        else:
            try:
                from datetime import datetime
                party_score = int(form_data['party_score'])
                date_entered = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                user_ip_address = request.remote_addr or 'unknown'
                conn.execute(
                    'INSERT INTO announced_pu_results (polling_unit_uniqueid, party_abbreviation, party_score, entered_by_user, date_entered, user_ip_address) VALUES (?, ?, ?, ?, ?, ?)',
                    (form_data['polling_unit_id'], form_data['party_abbreviation'], party_score, form_data['entered_by_user'], date_entered, user_ip_address)
                )
                conn.commit()
                message = 'Result saved successfully!'
                success = True
                form_data = {'polling_unit_id': '', 'party_abbreviation': '', 'party_score': '', 'entered_by_user': ''}
            except Exception as e:
                message = f'Error: {str(e)}'
    conn.close()

    return render_template(
        'q3_store_results.html',
        polling_units=polling_units,
        parties=parties,
        message=message,
        success=success,
        form_data=form_data
    )


if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)
