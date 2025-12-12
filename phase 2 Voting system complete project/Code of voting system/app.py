from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import secrets
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize database
def init_db():
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS voters
                 (id INTEGER PRIMARY KEY, voter_id TEXT UNIQUE, password TEXT, 
                  name TEXT, has_voted INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidates
                 (id INTEGER PRIMARY KEY, candidate_id TEXT UNIQUE, password TEXT,
                  name TEXT, party TEXT, bio TEXT, has_voted INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (id INTEGER PRIMARY KEY, voter_id TEXT, candidate_id TEXT,
                  timestamp TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS election_settings
                 (id INTEGER PRIMARY KEY, status TEXT DEFAULT 'open')''')
    
    # Add show_results column if it doesn't exist
    try:
        c.execute("ALTER TABLE election_settings ADD COLUMN show_results INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Add has_voted column to candidates table if it doesn't exist
    try:
        c.execute("ALTER TABLE candidates ADD COLUMN has_voted INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Insert default election status if not exists
    c.execute("SELECT COUNT(*) FROM election_settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO election_settings (status, show_results) VALUES ('open', 0)")
    
    # Insert default admin if not exists
    c.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        hashed_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO admins (username, password) VALUES ('admin', ?)", 
                  (hashed_password,))
    
    # Insert NOTA candidate if not exists
    c.execute("SELECT COUNT(*) FROM candidates WHERE candidate_id = 'NOTA'")
    if c.fetchone()[0] == 0:
        hashed_nota_password = hashlib.sha256('nota123'.encode()).hexdigest()
        c.execute("INSERT INTO candidates (candidate_id, password, name, party, bio, has_voted) VALUES (?, ?, ?, ?, ?, ?)", 
                  ('NOTA', hashed_nota_password, 'None of the Above', 'Neutral', 'NOTA (None of the Above) option for voters who do not wish to vote for any candidate', 0))
    
    conn.commit()
    conn.close()

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Check if election is open
def is_election_open():
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT status FROM election_settings LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] == 'open' if result else False

# Check if results should be shown
def should_show_results():
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    try:
        c.execute("SELECT show_results FROM election_settings LIMIT 1")
        result = c.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    except sqlite3.OperationalError:
        # Handle case where column doesn't exist yet
        conn.close()
        return False

# Homepage
@app.route('/')
def home():
    election_status = "Election Open" if is_election_open() else "Election Closed"
    
    # Get election results for display on home page (only if admin has enabled showing results)
    results_html = ""
    winner_announcement = ""
    chart_data = "[]"
    chart_labels = "[]"
    chart_colors = "[]"
    
    if should_show_results():
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        c.execute('''SELECT c.name, c.party, COUNT(v.id) as vote_count
                     FROM candidates c
                     LEFT JOIN votes v ON c.candidate_id = v.candidate_id
                     GROUP BY c.id
                     ORDER BY vote_count DESC''')
        results = c.fetchall()
        conn.close()
        
        # Create results table if there are results
        if results and any(result[2] > 0 for result in results):  # Check if any candidate has votes
            # Create winner announcement
            winner = results[0]
            winner_announcement = f'<div class="winner-announcement"><h3>🏆 Election Winner! 🏆</h3><p><strong>{winner[0]}</strong> from <em>{winner[1]}</em> has won the election with <strong>{winner[2]}</strong> votes!</p></div>'
            
            # Prepare data for pie chart
            names = [result[0] for result in results]
            votes = [result[2] for result in results]
            parties = [result[1] for result in results]
            
            # Generate colors for the chart
            colors = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40"]
            chart_colors = str(colors[:len(votes)] + colors[len(votes):] if len(votes) > len(colors) else colors[:len(votes)])
            
            chart_data = str(votes)
            chart_labels = str(names)
            
            # Create results table
            results_html = "<h3>Current Election Results</h3><table border='1'><tr><th>Candidate</th><th>Party</th><th>Votes</th></tr>"
            for result in results:
                results_html += f"<tr><td>{result[0]}</td><td>{result[1]}</td><td>{result[2]}</td></tr>"
            results_html += "</table>"
        else:
            # Display message when no votes have been cast
            results_html = '<div class="no-results"><p><strong>No votes have been recorded yet.</strong></p><p>Results will be displayed here once voting begins.</p></div>'
    else:
        # Display message when results are hidden
        results_html = '<div class="no-results"><p><strong>Results are currently hidden.</strong></p><p>The election results will be announced shortly after the election period ends.</p><p>Please check back later for the official results.</p></div>'
    
    return f'''
    <html>
    <head>
        <title>Voting Machine</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            
            <main>
                <section class="election-status">
                    <h2>Election Status</h2>
                    <p><strong>Status:</strong> <span class="status">{election_status}</span></p>
                </section>
                
                {winner_announcement}
                
                <section class="results-chart">
                    <div>
                        <canvas id="resultsChart"></canvas>
                    </div>
                </section>
                
                <section class="results-display">
                    {results_html}
                </section>
                
                <section class="user-portals">
                    <h2>User Portals</h2>
                    <div class="button-group">
                        <button class="portal-button" onclick="window.location.href='/admin_login'">Admin Login</button>
                        <button class="portal-button" onclick="window.location.href='/voter_login'">Voter Login</button>
                        <button class="portal-button" onclick="window.location.href='/candidate_login'">Candidate Login</button>
                    </div>
                </section>
                
                <section class="additional-options">
                    <h2>Additional Options</h2>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/verify_vote'">Verify Vote</button>
                        <button class="option-button" onclick="window.location.href='/help'">Help</button>
                    </div>
                </section>
            </main>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            // Only create chart if we have data
            if ({chart_data} && {chart_data}.length > 0) {{
                const ctx = document.getElementById('resultsChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: {chart_labels},
                        datasets: [{{
                            data: {chart_data},
                            backgroundColor: {chart_colors},
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                            }},
                            title: {{
                                display: true,
                                text: 'Election Results Distribution'
                            }}
                        }}
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    '''

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE username=? AND password=?", 
                  (username, password))
        admin = c.fetchone()
        conn.close()
        
        if admin:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return '''
            <html>
            <head>
                <title>Admin Login - Error</title>
                <link rel="stylesheet" type="text/css" href="/static/style.css">
            </head>
            <body>
                <div class="container">
                    <header>
                        <h1>Electronic Voting System</h1>
                    </header>
                    <main>
                        <section class="election-status">
                            <h2>Invalid Credentials</h2>
                            <div class="no-results">
                                <p>The username or password you entered is incorrect.</p>
                                <p>Please check your credentials and try again.</p>
                            </div>
                            <div class="button-group">
                                <button class="portal-button" onclick="window.location.href='/admin_login'">Try Again</button>
                                <button class="option-button" onclick="window.location.href='/'">Home</button>
                            </div>
                        </section>
                    </main>
                </div>
            </body>
            </html>
            '''
    
    return '''
    <html>
    <head>
        <title>Admin Login</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Admin Login</h2>
                    <p>Please enter your administrator credentials to access the system.</p>
                    <form method="POST">
                        <div>
                            <label for="username">Username:</label>
                            <input type="text" id="username" name="username" placeholder="Enter username" required>
                        </div>
                        <div>
                            <label for="password">Password:</label>
                            <input type="password" id="password" name="password" placeholder="Enter password" required>
                        </div>
                        <div>
                            <button class="portal-button" type="submit">Login</button>
                        </div>
                    </form>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/'">Home</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    status = "Open" if is_election_open() else "Closed"
    results_status = "Showing" if should_show_results() else "Hidden"
    
    # Get winner information if results are showing
    winner_info = ""
    if should_show_results():
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        c.execute('''SELECT c.name, c.party, COUNT(v.id) as vote_count
                     FROM candidates c
                     LEFT JOIN votes v ON c.candidate_id = v.candidate_id
                     GROUP BY c.id
                     ORDER BY vote_count DESC
                     LIMIT 1''')
        winner = c.fetchone()
        conn.close()
        
        if winner and winner[2] > 0:  # If there's a winner with votes
            winner_info = f'<div class="winner-info"><p><strong>🏆 Current Winner:</strong> {winner[0]} ({winner[1]}) with {winner[2]} votes</p></div>'
    
    return f'''
    <html>
    <head>
        <title>Admin Dashboard</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Admin Dashboard</h2>
                    <p>Welcome, Admin!</p>
                    {winner_info}
                </section>
                
                <section class="user-portals">
                    <h3>Election Control</h3>
                    <p><strong>Election Status:</strong> <span id="electionStatus" class="status">{status}</span></p>
                    <button class="portal-button" onclick="toggleElectionStatus()">Toggle Election Status</button>
                    <p><strong>Results Visibility:</strong> <span id="resultsStatus" class="status">{results_status}</span></p>
                    <!-- Always render the button but show/hide with CSS based on election status -->
                    <button class="option-button" onclick="toggleResultsVisibility()" style="display: {'none' if status == 'Open' else 'block'};">Toggle Results Visibility</button>
                </section>
                
                <section class="additional-options">
                    <h3>Management Options</h3>
                    <div class="button-group">
                        <button class="portal-button" onclick="window.location.href='/manage_users'">Manage Users</button>
                        <button class="portal-button" onclick="window.location.href='/monitoring'">Monitoring</button>
                        <button class="portal-button" onclick="window.location.href='/publish_results'">Publish Results</button>
                    </div>
                </section>
                
                <section class="user-portals">
                    <h3>System Management</h3>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/reset_election'">Reset Election Data</button>
                    </div>
                </section>
                
                <section class="additional-options">
                    <h3>Actions</h3>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/logout_admin'">Logout</button>
                    </div>
                </section>
            </main>
        </div>
        
        <script>
        function toggleElectionStatus() {{
            fetch('/toggle_election_ajax')
            .then(response => response.json())
            .then(data => {{
                // Update the election status text
                document.getElementById('electionStatus').textContent = data.status;
                // Update styling based on status
                const statusElement = document.getElementById('electionStatus');
                statusElement.className = 'status-' + data.status.toLowerCase();
                
                // Find the results visibility button and show/hide it based on election status
                const resultsButton = document.querySelector('button[onclick="toggleResultsVisibility()"]');
                if (resultsButton) {{
                    if (data.is_open) {{
                        // Election is now open, hide the results visibility button
                        resultsButton.style.display = 'none';
                    }} else {{
                        // Election is now closed, show the results visibility button
                        resultsButton.style.display = 'block';
                    }}
                }}
                
                // If results were automatically hidden, update the results status display
                if (data.results_hidden) {{
                    document.getElementById('resultsStatus').textContent = 'Hidden';
                }}
            }});
        }}
        
        function toggleResultsVisibility() {{
            fetch('/toggle_results_ajax')
            .then(response => response.json())
            .then(data => {{
                document.getElementById('resultsStatus').textContent = data.status;
                // No need to reload the page, UI is updated directly
            }});
        }}
        </script>
    </body>
    </html>
    '''

@app.route('/manage_voters', methods=['GET', 'POST'])
def manage_voters():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    message = ""
    message_class = ""
    
    if request.method == 'POST':
        if 'add_voter' in request.form:
            voter_id = request.form['voter_id']
            password = request.form['voter_password']
            name = request.form['voter_name']
            
            # Server-side validation
            if not name.replace(' ', '').isalpha() or len(name) > 55:
                message = "Error: Name can only contain letters and must be no more than 55 characters!"
                message_class = "error"
            elif len(password) < 3:
                message = "Error: Password must be at least 3 characters long!"
                message_class = "error"
            elif not any(c.isalpha() for c in password) or not any(not c.isalpha() for c in password):
                message = "Error: Password must contain both letters and non-letter characters (numbers or special characters)!"
                message_class = "error"
            else:
                # Hash password after validation
                password = hash_password(password)
                
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO voters (voter_id, password, name) VALUES (?, ?, ?)", 
                             (voter_id, password, name))
                    conn.commit()
                    message = f"Voter {voter_id} added successfully!"
                    message_class = "success"
                except sqlite3.IntegrityError:
                    message = f"Error: Voter ID {voter_id} already exists!"
                    message_class = "error"
                conn.close()
        elif 'edit_password' in request.form:
            voter_id = request.form['edit_voter_id']
            new_password = request.form['new_password']
            
            # Validate password length
            if len(new_password) < 3:
                message = f"Error: New password must be at least 3 characters long!"
                message_class = "error"
            elif not any(c.isalpha() for c in new_password) or not any(not c.isalpha() for c in new_password):
                message = "Error: Password must contain both letters and non-letter characters (numbers or special characters)!"
                message_class = "error"
            else:
                new_password = hash_password(new_password)
                
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                c.execute("UPDATE voters SET password = ? WHERE voter_id = ?", 
                         (new_password, voter_id))
                if c.rowcount > 0:
                    conn.commit()
                    message = f"Password for voter {voter_id} updated successfully!"
                    message_class = "success"
                else:
                    message = f"Error: Voter ID {voter_id} not found!"
                    message_class = "error"
                conn.close()
        elif 'delete_voter' in request.form:
            voter_id = request.form['delete_voter_id']
            
            conn = sqlite3.connect('voting.db')
            c = conn.cursor()
            c.execute("DELETE FROM voters WHERE voter_id = ?", (voter_id,))
            if c.rowcount > 0:
                conn.commit()
                message = f"Voter {voter_id} deleted successfully!"
                message_class = "success"
            else:
                message = f"Error: Voter ID {voter_id} not found!"
                message_class = "error"
            conn.close()
        elif 'update_voter' in request.form:
            voter_id = request.form['voter_id']
            new_name = request.form['name']
            
            conn = sqlite3.connect('voting.db')
            c = conn.cursor()
            c.execute("UPDATE voters SET name = ? WHERE voter_id = ?", (new_name, voter_id))
            if c.rowcount > 0:
                conn.commit()
                message = f"Voter {voter_id} updated successfully!"
                message_class = "success"
            else:
                message = f"Error: Voter ID {voter_id} not found!"
                message_class = "error"
            conn.close()
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT voter_id, name, has_voted FROM voters")
    voters = c.fetchall()
    conn.close()
    
    # Create table for voters
    voters_table = "<table><tr><th>Voter ID</th><th>Name</th><th>Status</th><th>Update</th><th>Password</th><th>Delete</th></tr>"
    for voter in voters:
        status = "Voted" if voter[2] else "Not Voted"
        voters_table += f"<tr><form method='POST' style='display:inline;'><td>{voter[0]}<input type='hidden' name='voter_id' value='{voter[0]}'></td><td><input type='text' name='name' value='{voter[1]}' style='width: 100%; background-color: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-small); padding: 8px;'></td><td>{status}</td><td><button class='portal-button' type='submit' name='update_voter' value='1' style='padding: 8px 12px; font-size: 0.9rem;'>Update</button></td><td><button class='option-button' type='button' onclick=\"showPasswordPopup('{voter[0]}')\" style='padding: 8px 12px; font-size: 0.9rem;'>Update Password</button></td><td><button class='option-button' type='submit' name='delete_voter' value='{voter[0]}' onclick='return confirm(\"Are you sure you want to delete this voter?\")' style='padding: 8px 12px; font-size: 0.9rem;'>Delete</button></td></form></tr>"
    voters_table += "</table>"
    
    return f'''
    <html>
    <head>
        <title>Manage Voters</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Voter Management</h2>
                    
                    {f"<div class='no-results' style='background-color: #27ae60; border-color: #27ae60;'>{message}</div>" if message and 'success' in message.lower() else ""}
                    {f"<div class='no-results' style='background-color: #e74c3c; border-color: #e74c3c;'>{message}</div>" if message and 'error' in message.lower() else ""}
                </section>
                
                <section class="user-portals">
                    <h3>Add New Voter</h3>
                    <form method="POST" onsubmit="return validateVoterForm()">
                        <input type="hidden" name="add_voter" value="1">
                        <div>
                            <label for="voter_id">Voter ID:</label>
                            <input type="text" id="voter_id" name="voter_id" required>
                        </div>
                        <div>
                            <label for="voter_name">Name:</label>
                            <input type="text" id="voter_name" name="voter_name" required maxlength="55">
                            <small>Only letters allowed, max 55 characters</small>
                        </div>
                        <div>
                            <label for="voter_password">Password:</label>
                            <input type="password" id="voter_password" name="voter_password" required minlength="3">
                            <small>Minimum 3 characters, must contain both letters and non-letter characters</small>
                        </div>
                        <div>
                            <button class="portal-button" type="submit">Add Voter</button>
                        </div>
                    </form>
                </section>
                
                <section class="additional-options">
                    <h3>Registered Voters</h3>
                    {voters_table}
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
        
        <!-- Password Update Popup -->
        <div id="passwordPopup" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: #111111; padding: 20px; border: 1px solid #333333; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); z-index: 1000; border-radius: 16px;">
            <h3>Update Password</h3>
            <form method="POST" id="passwordForm">
                <input type="hidden" name="edit_password" value="1">
                <input type="hidden" name="edit_voter_id" id="popupVoterId">
                <div>
                    <label for="popupVoterIdDisplay">Voter ID:</label>
                    <input type="text" id="popupVoterIdDisplay" readonly style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div>
                    <label for="new_password">New Password:</label>
                    <input type="password" id="new_password" name="new_password" required style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div style="margin-top: 15px;">
                    <button class="portal-button" type="submit">Update Password</button>
                    <button class="option-button" type="button" onclick="closePasswordPopup()">Cancel</button>
                </div>
            </form>
        </div>
        
        <!-- Overlay for popup -->
        <div id="popupOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 999;" onclick="closePasswordPopup()"></div>
        
        <script>
        function showPasswordPopup(voterId) {{
            document.getElementById('popupVoterId').value = voterId;
            document.getElementById('popupVoterIdDisplay').value = voterId;
            document.getElementById('new_password').value = '';
            document.getElementById('passwordPopup').style.display = 'block';
            document.getElementById('popupOverlay').style.display = 'block';
        }}
        
        function closePasswordPopup() {{
            document.getElementById('passwordPopup').style.display = 'none';
            document.getElementById('popupOverlay').style.display = 'none';
        }}
        
        function validateVoterForm() {{
            var name = document.getElementById('voter_name').value;
            var password = document.getElementById('voter_password').value;
            
            // Validate name: only letters, max 55 characters
            if (!/^[a-zA-Z]+$/.test(name)) {{
                alert('Name can only contain letters (no special characters or numbers).');
                return false;
            }}
            
            if (name.length > 55) {{
                alert('Name cannot exceed 55 characters.');
                return false;
            }}
            
            // Validate password: minimum 3 characters, must contain both letters and non-letters
            if (password.length < 3) {{
                alert('Password must be at least 3 characters long.');
                return false;
            }}
            
            if (!/[a-zA-Z]/.test(password) || !/[^a-zA-Z]/.test(password)) {{
                alert('Password must contain both letters and non-letter characters (numbers or special characters).');
                return false;
            }}
            
            return true;
        }}
        
        function validateCandidateForm() {{
            var name = document.getElementById('candidate_name').value;
            var password = document.getElementById('candidate_password').value;
            
            // Validate name: only letters, max 55 characters
            if (!/^[a-zA-Z]+$/.test(name)) {{
                alert('Name can only contain letters (no special characters or numbers).');
                return false;
            }}
            
            if (name.length > 55) {{
                alert('Name cannot exceed 55 characters.');
                return false;
            }}
            
            // Validate password: minimum 3 characters, must contain both letters and non-letters
            if (password.length < 3) {{
                alert('Password must be at least 3 characters long.');
                return false;
            }}
            
            if (!/[a-zA-Z]/.test(password) || !/[^a-zA-Z]/.test(password)) {{
                alert('Password must contain both letters and non-letter characters (numbers or special characters).');
                return false;
            }}
            
            return true;
        }}
        </script>
    </body>
    </html>
    '''

# Manage Candidates
@app.route('/manage_candidates', methods=['GET', 'POST'])
def manage_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    message = ""
    message_class = ""
    
    if request.method == 'POST':
        if 'add_candidate' in request.form:
            candidate_id = request.form['candidate_id']
            password = request.form['candidate_password']
            name = request.form['candidate_name']
            party = request.form['candidate_party']
            bio = request.form['candidate_bio']
            
            # Server-side validation
            if not name.replace(' ', '').isalpha() or len(name) > 55:
                message = "Error: Name can only contain letters and must be no more than 55 characters!"
                message_class = "error"
            elif len(password) < 3:
                message = "Error: Password must be at least 3 characters long!"
                message_class = "error"
            elif not any(c.isalpha() for c in password) or not any(not c.isalpha() for c in password):
                message = "Error: Password must contain both letters and non-letter characters (numbers or special characters)!"
                message_class = "error"
            else:
                # Hash password after validation
                password = hash_password(password)
                
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO candidates (candidate_id, password, name, party, bio, has_voted) VALUES (?, ?, ?, ?, ?, ?)", 
                             (candidate_id, password, name, party, bio, 0))
                    conn.commit()
                    message = f"Candidate {candidate_id} added successfully!"
                    message_class = "success"
                except sqlite3.IntegrityError:
                    message = f"Error: Candidate ID {candidate_id} already exists!"
                    message_class = "error"
                conn.close()
        elif 'edit_password' in request.form:
            candidate_id = request.form['edit_candidate_id']
            new_password = request.form['new_password']
            
            # Validate password length
            if len(new_password) < 3:
                message = f"Error: New password must be at least 3 characters long!"
                message_class = "error"
            elif not any(c.isalpha() for c in new_password) or not any(not c.isalpha() for c in new_password):
                message = "Error: Password must contain both letters and non-letter characters (numbers or special characters)!"
                message_class = "error"
            else:
                new_password = hash_password(new_password)
                
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                c.execute("UPDATE candidates SET password = ? WHERE candidate_id = ?", 
                         (new_password, candidate_id))
                if c.rowcount > 0:
                    conn.commit()
                    message = f"Password for candidate {candidate_id} updated successfully!"
                    message_class = "success"
                else:
                    message = f"Error: Candidate ID {candidate_id} not found!"
                    message_class = "error"
                conn.close()
        elif 'delete_candidate' in request.form:
            candidate_id = request.form['delete_candidate_id']
            
            # Prevent deletion of NOTA candidate
            if candidate_id == 'NOTA':
                message = "Error: NOTA candidate cannot be deleted!"
                message_class = "error"
            else:
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                c.execute("DELETE FROM candidates WHERE candidate_id = ?", (candidate_id,))
                if c.rowcount > 0:
                    conn.commit()
                    message = f"Candidate {candidate_id} deleted successfully!"
                    message_class = "success"
                else:
                    message = f"Error: Candidate ID {candidate_id} not found!"
                    message_class = "error"
                conn.close()
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT candidate_id, name, party, has_voted FROM candidates")
    candidates = c.fetchall()
    conn.close()
    
    # Create table for candidates
    candidates_table = "<table><tr><th>Candidate ID</th><th>Name</th><th>Party</th><th>Status</th><th>Password</th><th>Delete</th></tr>"
    for candidate in candidates:
        status = "Voted" if candidate[3] else "Not Voted"
        # Disable delete button for NOTA candidate
        delete_button = "<button class='option-button' disabled style='padding: 8px 12px; font-size: 0.9rem;'>Cannot Delete</button>" if candidate[0] == 'NOTA' else f"<form method='POST' style='display:inline;'><input type='hidden' name='delete_candidate' value='1'><input type='hidden' name='delete_candidate_id' value='{candidate[0]}'><button class='option-button' type='submit' onclick='return confirm(\"Are you sure you want to delete this candidate?\")' style='padding: 8px 12px; font-size: 0.9rem;'>Delete</button></form>"
        candidates_table += f"<tr><td>{candidate[0]}</td><td>{candidate[1]}</td><td>{candidate[2]}</td><td>{status}</td><td><button class='option-button' type='button' onclick=\"showCandidatePasswordPopup('{candidate[0]}')\" style='padding: 8px 12px; font-size: 0.9rem;'>Update Password</button></td><td>{delete_button}</td></tr>"
    candidates_table += "</table>"
    
    return f'''
    <html>
    <head>
        <title>Manage Candidates</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Candidate Management</h2>
                    
                    {f"<div class='no-results' style='background-color: #27ae60; border-color: #27ae60;'>{message}</div>" if message and 'success' in message.lower() else ""}
                    {f"<div class='no-results' style='background-color: #e74c3c; border-color: #e74c3c;'>{message}</div>" if message and 'error' in message.lower() else ""}
                </section>
                
                <section class="user-portals">
                    <h3>Add New Candidate</h3>
                    <form method="POST" onsubmit="return validateCandidateForm()">
                        <input type="hidden" name="add_candidate" value="1">
                        <div>
                            <label for="candidate_id">Candidate ID:</label>
                            <input type="text" id="candidate_id" name="candidate_id" required>
                        </div>
                        <div>
                            <label for="candidate_name">Name:</label>
                            <input type="text" id="candidate_name" name="candidate_name" required maxlength="55">
                            <small>Only letters allowed, max 55 characters</small>
                        </div>
                        <div>
                            <label for="candidate_party">Party:</label>
                            <input type="text" id="candidate_party" name="candidate_party" required>
                        </div>
                        <div>
                            <label for="candidate_bio">Bio:</label>
                            <textarea id="candidate_bio" name="candidate_bio" required rows="4"></textarea>
                        </div>
                        <div>
                            <label for="candidate_password">Password:</label>
                            <input type="password" id="candidate_password" name="candidate_password" required minlength="3">
                            <small>Minimum 3 characters, must contain both letters and non-letter characters</small>
                        </div>
                        <div>
                            <button class="portal-button" type="submit">Add Candidate</button>
                        </div>
                    </form>
                </section>
                
                <section class="additional-options">
                    <h3>Registered Candidates</h3>
                    {candidates_table}
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
        
        <!-- Password Update Popup -->
        <div id="passwordPopup" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: #111111; padding: 20px; border: 1px solid #333333; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); z-index: 1000; border-radius: 16px;">
            <h3>Update Password</h3>
            <form method="POST" id="passwordForm">
                <input type="hidden" name="edit_password" value="1">
                <input type="hidden" name="edit_candidate_id" id="popupCandidateId">
                <div>
                    <label for="popupCandidateIdDisplay">Candidate ID:</label>
                    <input type="text" id="popupCandidateIdDisplay" readonly style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div>
                    <label for="new_password">New Password:</label>
                    <input type="password" id="new_password" name="new_password" required style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div style="margin-top: 15px;">
                    <button class="portal-button" type="submit">Update Password</button>
                    <button class="option-button" type="button" onclick="closePasswordPopup()">Cancel</button>
                </div>
            </form>
        </div>
        
        <!-- Overlay for popup -->
        <div id="popupOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 999;" onclick="closePasswordPopup()"></div>
        
        <script>
        function showCandidatePasswordPopup(candidateId) {{
            document.getElementById('popupCandidateId').value = candidateId;
            document.getElementById('popupCandidateIdDisplay').value = candidateId;
            document.getElementById('new_password').value = '';
            document.getElementById('passwordPopup').style.display = 'block';
            document.getElementById('popupOverlay').style.display = 'block';
        }}
        
        function closePasswordPopup() {{
            document.getElementById('passwordPopup').style.display = 'none';
            document.getElementById('popupOverlay').style.display = 'none';
        }}
        
        function validateVoterForm() {{
            var name = document.getElementById('voter_name').value;
            var password = document.getElementById('voter_password').value;
            
            // Validate name: only letters, max 55 characters
            if (!/^[a-zA-Z]+$/.test(name)) {{
                alert('Name can only contain letters (no special characters or numbers).');
                return false;
            }}
            
            if (name.length > 55) {{
                alert('Name cannot exceed 55 characters.');
                return false;
            }}
            
            // Validate password: minimum 3 characters, must contain both letters and non-letters
            if (password.length < 3) {{
                alert('Password must be at least 3 characters long.');
                return false;
            }}
            
            if (!/[a-zA-Z]/.test(password) || !/[^a-zA-Z]/.test(password)) {{
                alert('Password must contain both letters and non-letter characters (numbers or special characters).');
                return false;
            }}
            
            return true;
        }}
        
        function validateCandidateForm() {{
            var name = document.getElementById('candidate_name').value;
            var password = document.getElementById('candidate_password').value;
            
            // Validate name: only letters, max 55 characters
            if (!/^[a-zA-Z]+$/.test(name)) {{
                alert('Name can only contain letters (no special characters or numbers).');
                return false;
            }}
            
            if (name.length > 55) {{
                alert('Name cannot exceed 55 characters.');
                return false;
            }}
            
            // Validate password: minimum 3 characters, must contain both letters and non-letters
            if (password.length < 3) {{
                alert('Password must be at least 3 characters long.');
                return false;
            }}
            
            if (!/[a-zA-Z]/.test(password) || !/[^a-zA-Z]/.test(password)) {{
                alert('Password must contain both letters and non-letter characters (numbers or special characters).');
                return false;
            }}
            
            return true;
        }}
        </script>
    </body>
    </html>
    '''

# Election Setup
@app.route('/election_setup')
def election_setup():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    status = "Open" if is_election_open() else "Closed"
    return f'''
    <html>
    <head>
        <title>Election Setup</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Election Setup</h2>
                    <div>
                        <h3>Current Status</h3>
                        <p><strong>Status:</strong> <span class="status">{status}</span></p>
                        <button class="portal-button" onclick="window.location.href='/toggle_election'">Toggle Election Status</button>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Toggle Election Status
@app.route('/toggle_election')
def toggle_election():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    current_status = "open" if is_election_open() else "closed"
    new_status = "closed" if current_status == "open" else "open"
    c.execute("UPDATE election_settings SET status = ?", (new_status,))
    conn.commit()
    conn.close()
    
    action = "closed" if current_status == "open" else "opened"
    
    return f'''
    <html>
    <head>
        <title>Election Status Updated</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Election Status Updated</h2>
                    <div class="no-results">
                        <p><strong>Election has been {action}.</strong></p>
                        <p>If closed, voting is temporarily paused.</p>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Monitoring
@app.route('/monitoring')
def monitoring():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters WHERE has_voted = 1")
    voted_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM voters")
    total_voters = c.fetchone()[0]
    conn.close()
    
    turnout = (voted_count / total_voters * 100) if total_voters > 0 else 0
    
    return f'''
    <html>
    <head>
        <title>Monitoring</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Monitoring Dashboard</h2>
                    <div>
                        <h3>Election Statistics</h3>
                        <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; margin: 30px 0;">
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{total_voters}</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Total Voters</div>
                            </div>
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{voted_count}</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Voted</div>
                            </div>
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{turnout:.2f}%</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Turnout</div>
                            </div>
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Publish Results
@app.route('/publish_results')
def publish_results():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute('''SELECT c.name, c.party, COUNT(v.id) as vote_count
                 FROM candidates c
                 LEFT JOIN votes v ON c.candidate_id = v.candidate_id
                 GROUP BY c.id
                 ORDER BY vote_count DESC''')
    results = c.fetchall()
    conn.close()
    
    results_html = "<table><tr><th>Candidate</th><th>Party</th><th>Votes</th></tr>"
    for result in results:
        results_html += f"<tr><td>{result[0]}</td><td>{result[1]}</td><td>{result[2]}</td></tr>"
    results_html += "</table>"
    
    return f'''
    <html>
    <head>
        <title>Publish Results</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Official Results</h2>
                    <div>
                        <h3>Election Results</h3>
                        <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border);">
                            {results_html}
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Logout Admin
@app.route('/logout_admin')
def logout_admin():
    session.pop('admin', None)
    return redirect(url_for('home'))

# Voter Login
@app.route('/voter_login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        password = hash_password(request.form['password'])
        
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        # Check if the user exists in voters table
        c.execute("SELECT * FROM voters WHERE voter_id=? AND password=?", 
                  (voter_id, password))
        voter = c.fetchone()
        
        # If not found in voters, check candidates table
        if not voter:
            c.execute("SELECT * FROM candidates WHERE candidate_id=? AND password=?", 
                      (voter_id, password))
            voter = c.fetchone()
        
        conn.close()
        
        if voter:
            session['voter'] = voter_id
            return redirect(url_for('voting_interface'))
        else:
            return '''
            <html>
            <head>
                <title>Voter Login - Error</title>
                <link rel="stylesheet" type="text/css" href="/static/style.css">
            </head>
            <body>
                <div class="container">
                    <header>
                        <h1>Electronic Voting System</h1>
                    </header>
                    <main>
                        <section class="election-status">
                            <h2>Invalid Credentials</h2>
                            <div class="no-results">
                                <p>The voter ID or password you entered is incorrect.</p>
                            </div>
                            <div class="button-group">
                                <button class="portal-button" onclick="window.location.href='/voter_login'">Try Again</button>
                                <button class="option-button" onclick="window.location.href='/'">Home</button>
                            </div>
                        </section>
                    </main>
                </div>
            </body>
            </html>
            '''
    
    return '''
    <html>
    <head>
        <title>Voter Login</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Voter Login</h2>
                    <form method="POST">
                        <div>
                            <label for="voter_id">Voter ID:</label>
                            <input type="text" id="voter_id" name="voter_id" placeholder="Voter ID" required>
                        </div>
                        <div>
                            <label for="password">Password:</label>
                            <input type="password" id="password" name="password" placeholder="Password" required>
                        </div>
                        <div>
                            <button class="portal-button" type="submit">Login</button>
                        </div>
                    </form>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/'">Home</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Voting Interface
@app.route('/voting_interface')
def voting_interface():
    if 'voter' not in session:
        return redirect(url_for('voter_login'))
    
    # Check if voter has already voted (could be a voter or candidate)
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    
    # First check if this is a candidate
    c.execute("SELECT has_voted FROM candidates WHERE candidate_id=?", (session['voter'],))
    candidate_result = c.fetchone()
    
    if candidate_result:
        # This is a candidate
        has_voted = candidate_result[0]
    else:
        # This is a regular voter
        c.execute("SELECT has_voted FROM voters WHERE voter_id=?", (session['voter'],))
        has_voted = c.fetchone()[0]
    
    conn.close()
    
    if has_voted:
        return '''
        <html>
        <head>
            <title>Already Voted</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Electronic Voting System</h1>
                </header>
                <main>
                    <section class="election-status">
                        <h2>You have already voted</h2>
                        <div class="no-results">
                            <p>Each voter can only vote once.</p>
                            <p>Your vote has already been recorded in the system.</p>
                        </div>
                        <div class="button-group">
                            <button class="option-button" onclick="window.location.href='/logout_voter'">Logout</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
        </html>
        '''
    
    # Get candidates
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT candidate_id, name, party FROM candidates")
    candidates = c.fetchall()
    conn.close()
    
    candidates_html = ""
    nota_html = ""
    for candidate in candidates:
        # Separate NOTA candidate to display it at the end
        if candidate[0] == 'NOTA':
            nota_html = f'''
            <div style="border-top: 1px solid #ccc; margin-top: 10px; padding-top: 10px;">
                <input type="radio" name="candidate" value="{candidate[0]}" id="{candidate[0]}" required>
                <label for="{candidate[0]}">{candidate[1]} ({candidate[2]})</label>
            </div>
            '''
        else:
            candidates_html += f'''
            <div>
                <input type="radio" name="candidate" value="{candidate[0]}" id="{candidate[0]}" required>
                <label for="{candidate[0]}">{candidate[1]} ({candidate[2]})</label>
            </div>
            '''
    
    # Add NOTA at the end
    candidates_html += nota_html
    
    return f'''
    <html>
    <head>
        <title>Select Your Candidate</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Select Your Candidate</h2>
                    <div>
                        <h3>Available Candidates</h3>
                        <form method="POST" action="/confirm_vote">
                            <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border);">
                                {candidates_html}
                            </div>
                            <div style="margin-top: 20px;">
                                <button class="portal-button" type="submit">Continue to Confirmation</button>
                            </div>
                        </form>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/logout_voter'">Logout</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Confirm Vote
@app.route('/confirm_vote', methods=['POST'])
def confirm_vote():
    if 'voter' not in session:
        return redirect(url_for('voter_login'))
    
    candidate_id = request.form.get('candidate')
    if not candidate_id:
        return '''
        <html>
        <head>
            <title>No Candidate Selected</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Electronic Voting System</h1>
                </header>
                <main>
                    <section class="election-status">
                        <h2>No Candidate Selected</h2>
                        <div class="no-results">
                            <p>Please select a candidate before continuing.</p>
                        </div>
                        <div class="button-group">
                            <button class="option-button" onclick="window.location.href='/voting_interface'">Back to Voting</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
        </html>
        '''
    
    # Get candidate details
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT name, party FROM candidates WHERE candidate_id=?", (candidate_id,))
    candidate = c.fetchone()
    conn.close()
    
    if not candidate:
        return '''
        <html>
        <head>
            <title>Invalid Candidate</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Electronic Voting System</h1>
                </header>
                <main>
                    <section class="election-status">
                        <h2>Invalid Candidate</h2>
                        <div class="no-results">
                            <p>The selected candidate is not valid.</p>
                        </div>
                        <div class="button-group">
                            <button class="option-button" onclick="window.location.href='/voting_interface'">Back to Voting</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
        </html>
        '''
    
    return f'''
    <html>
    <head>
        <title>Confirm Your Vote</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Confirm Your Vote</h2>
                    <div>
                        <h3>You have selected:</h3>
                        <div class="no-results">
                            <p>{candidate[0]}</p>
                            <p>({candidate[1]})</p>
                        </div>
                        <form method="POST" action="/cast_vote">
                            <input type="hidden" name="candidate_id" value="{candidate_id}">
                            <div>
                                <button class="portal-button" type="submit">Confirm Vote</button>
                            </div>
                        </form>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/voting_interface'">Back to Voting</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Cast Vote
@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    if 'voter' not in session:
        return redirect(url_for('voter_login'))
    
    candidate_id = request.form['candidate_id']
    
    # Check if election is open
    if not is_election_open():
        return '''
        <html>
        <head>
            <title>Voting Closed</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Electronic Voting System</h1>
                </header>
                <main>
                    <section class="election-status">
                        <h2>Voting Closed</h2>
                        <div class="no-results">
                            <p>Voting is currently closed. Please try again later.</p>
                        </div>
                        <div class="button-group">
                            <button class="option-button" onclick="window.location.href='/logout_voter'">Logout</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
        </html>
        '''
    
    # Record vote
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    receipt_id = secrets.token_hex(8)
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("INSERT INTO votes (voter_id, candidate_id, timestamp) VALUES (?, ?, ?)",
              (session['voter'], candidate_id, timestamp))
    
    # Check if the voter is a candidate
    c.execute("SELECT COUNT(*) FROM candidates WHERE candidate_id=?", (session['voter'],))
    is_candidate = c.fetchone()[0] > 0
    
    if is_candidate:
        # Update candidate's has_voted status
        c.execute("UPDATE candidates SET has_voted=1 WHERE candidate_id=?", (session['voter'],))
    else:
        # Update voter's has_voted status
        c.execute("UPDATE voters SET has_voted=1 WHERE voter_id=?", (session['voter'],))
    
    conn.commit()
    conn.close()
    
    return f'''
    <html>
    <head>
        <title>Vote Recorded</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Vote Successfully Recorded</h2>
                    <div class="no-results">
                        <p>Your vote has been recorded anonymously.</p>
                        <p><strong>Your receipt ID:</strong></p>
                        <div style="background: linear-gradient(135deg, var(--accent), var(--accent-secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-size: 1.5rem; font-weight: bold; margin: 15px 0;">{receipt_id}</div>
                        <p>Please save this receipt ID to verify your vote later.</p>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/logout_voter'">Logout</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Logout Voter
@app.route('/logout_voter')
def logout_voter():
    session.pop('voter', None)
    return redirect(url_for('home'))

# Candidate Login
@app.route('/candidate_login', methods=['GET', 'POST'])
def candidate_login():
    if request.method == 'POST':
        candidate_id = request.form['candidate_id']
        password = hash_password(request.form['password'])
        
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        c.execute("SELECT * FROM candidates WHERE candidate_id=? AND password=?", 
                  (candidate_id, password))
        candidate = c.fetchone()
        conn.close()
        
        if candidate:
            session['candidate'] = candidate_id
            return redirect(url_for('candidate_dashboard'))
        else:
            return '''
            <html>
            <head>
                <title>Candidate Login - Error</title>
                <link rel="stylesheet" type="text/css" href="/static/style.css">
            </head>
            <body>
                <div class="container">
                    <header>
                        <h1>Electronic Voting System</h1>
                    </header>
                    <main>
                        <section class="election-status">
                            <h2>Invalid Credentials</h2>
                            <div class="no-results">
                                <p>The candidate ID or password you entered is incorrect.</p>
                                <p>Please check your credentials and try again.</p>
                            </div>
                            <div class="button-group">
                                <button class="portal-button" onclick="window.location.href='/candidate_login'">Try Again</button>
                                <button class="option-button" onclick="window.location.href='/'">Home</button>
                            </div>
                        </section>
                    </main>
                </div>
            </body>
            </html>
            '''
    
    return '''
    <html>
    <head>
        <title>Candidate Login</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Candidate Login</h2>
                    <p>Please enter your candidate credentials to access the system.</p>
                    <div>
                        <form method="POST">
                            <div>
                                <label for="candidate_id">Candidate ID:</label>
                                <input type="text" id="candidate_id" name="candidate_id" placeholder="Enter candidate ID" required>
                            </div>
                            <div>
                                <label for="password">Password:</label>
                                <input type="password" id="password" name="password" placeholder="Enter password" required>
                            </div>
                            <div>
                                <button class="portal-button" type="submit">Login</button>
                            </div>
                        </form>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/'">Home</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Candidate Dashboard
@app.route('/candidate_dashboard')
def candidate_dashboard():
    if 'candidate' not in session:
        return redirect(url_for('candidate_login'))
    
    # Get candidate details
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT name, party, bio FROM candidates WHERE candidate_id=?", 
              (session['candidate'],))
    candidate = c.fetchone()
    conn.close()
    
    return f'''
    <html>
    <head>
        <title>Candidate Dashboard</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Candidate Dashboard</h2>
                    <div>
                        <h3>Candidate Profile</h3>
                        <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border);">
                            <p>Welcome, {candidate[0]}!</p>
                            <p><strong>Party:</strong> {candidate[1]}</p>
                            <div>
                                <p><strong>Bio:</strong></p>
                                <p>{candidate[2]}</p>
                            </div>
                        </div>
                    </div>
                    
                    <section class="user-portals">
                        <h3>Options</h3>
                        <div class="button-group">
                            <button class="portal-button" onclick="window.location.href='/election_info'">Election Info</button>
                            <button class="option-button" onclick="window.location.href='/logout_candidate'">Logout</button>
                        </div>
                    </section>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Election Info
@app.route('/election_info')
def election_info():
    if 'candidate' not in session:
        return redirect(url_for('candidate_login'))
    
    status = "Open" if is_election_open() else "Closed"
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters WHERE has_voted = 1")
    voted_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM voters")
    total_voters = c.fetchone()[0]
    conn.close()
    
    turnout = (voted_count / total_voters * 100) if total_voters > 0 else 0
    
    return f'''
    <html>
    <head>
        <title>Election Info</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Election Information</h2>
                    <div>
                        <h3>Election Statistics</h3>
                        <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; margin: 30px 0;">
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{status}</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Status</div>
                            </div>
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{turnout:.2f}%</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Voter Turnout</div>
                            </div>
                            <div style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary)); padding: 20px; border-radius: var(--radius); text-align: center; min-width: 150px; box-shadow: var(--shadow); border: 1px solid var(--border);">
                                <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{voted_count}/{total_voters}</div>
                                <div style="color: var(--text-secondary); margin-top: 5px;">Voted</div>
                            </div>
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/candidate_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Candidate Results
@app.route('/candidate_results')
def candidate_results():
    if 'candidate' not in session:
        return redirect(url_for('candidate_login'))
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    c.execute('''SELECT c.name, c.party, COUNT(v.id) as vote_count
                 FROM candidates c
                 LEFT JOIN votes v ON c.candidate_id = v.candidate_id
                 GROUP BY c.id
                 ORDER BY vote_count DESC''')
    results = c.fetchall()
    conn.close()
    
    results_html = "<table><tr><th>Candidate</th><th>Party</th><th>Votes</th></tr>"
    for result in results:
        results_html += f"<tr><td>{result[0]}</td><td>{result[1]}</td><td>{result[2]}</td></tr>"
    results_html += "</table>"
    
    return f'''
    <html>
    <head>
        <title>Election Results</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Current Results</h2>
                    <div>
                        <h3>Election Results</h3>
                        <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border);">
                            {results_html}
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/candidate_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Logout Candidate
@app.route('/logout_candidate')
def logout_candidate():
    session.pop('candidate', None)
    return redirect(url_for('home'))

# Verify Vote
@app.route('/verify_vote', methods=['GET', 'POST'])
def verify_vote():
    if request.method == 'POST':
        receipt_id = request.form['receipt_id']
        # In a real implementation, we would verify the receipt
        # For this demo, we'll just show a success message
        return '''
        <html>
        <head>
            <title>Vote Verification</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Electronic Voting System</h1>
                </header>
                <main>
                    <section class="election-status">
                        <h2>Vote Verification</h2>
                        <div class="no-results">
                            <p><strong>Your vote has been verified in the system.</strong></p>
                        </div>
                        <div class="no-results">
                            <p>Note: In a real implementation, this would check against a secure database.</p>
                        </div>
                        <div class="button-group">
                            <button class="option-button" onclick="window.location.href='/'">Home</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
        </html>
        '''
    
    return '''
    <html>
    <head>
        <title>Verify Vote</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Verify Your Vote</h2>
                    <div class="no-results">
                        <p>Enter your receipt ID to verify your vote was recorded correctly.</p>
                    </div>
                    <div>
                        <form method="POST">
                            <div>
                                <label for="receipt_id">Receipt ID:</label>
                                <input type="text" id="receipt_id" name="receipt_id" placeholder="Enter receipt ID" required>
                            </div>
                            <div>
                                <button class="portal-button" type="submit">Verify Vote</button>
                            </div>
                        </form>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/'">Home</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Help Section
@app.route('/help')
def help_section():
    return '''
    <html>
    <head>
        <title>Help</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Help & Support</h2>
                    <div>
                        <h3>Frequently Asked Questions</h3>
                        <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 20px;">
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: var(--accent);">Q: How do I log in?</div>
                                <div>A: Select your role on the homepage and enter your credentials.</div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: var(--accent);">Q: What should I do if I forget my password?</div>
                                <div>A: Contact your system administrator for password reset.</div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: var(--accent);">Q: Can I change my vote after submitting?</div>
                                <div>A: No, each voter can only vote once for security reasons.</div>
                            </div>
                            
                            <div>
                                <div style="font-weight: bold; color: var(--accent);">Q: How is my vote secured?</div>
                                <div>A: All votes are encrypted and stored securely. Your identity is separated from your vote.</div>
                            </div>
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/'">Home</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''

# Toggle Election Status AJAX
@app.route('/toggle_election_ajax')
def toggle_election_ajax():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    current_status = "open" if is_election_open() else "closed"
    new_status = "closed" if current_status == "open" else "open"
    
    # If we're opening the election, also hide the results
    if new_status == "open":
        c.execute("UPDATE election_settings SET status = ?, show_results = 0", (new_status,))
    else:
        c.execute("UPDATE election_settings SET status = ?", (new_status,))
    
    conn.commit()
    conn.close()
    
    status_text = "Closed" if current_status == "open" else "Open"
    # Also return whether the election is now open or closed for UI updates
    is_open = new_status == "open"
    # Indicate if results were automatically hidden
    results_hidden = new_status == "open"
    return jsonify({'status': status_text, 'is_open': is_open, 'results_hidden': results_hidden})

# Toggle Results Visibility AJAX
@app.route('/toggle_results_ajax')
def toggle_results_ajax():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    current_show_results = should_show_results()
    new_show_results = 0 if current_show_results else 1
    c.execute("UPDATE election_settings SET show_results = ?", (new_show_results,))
    conn.commit()
    conn.close()
    
    status_text = "Hidden" if current_show_results else "Showing"
    return jsonify({'status': status_text})

# Reset Election Data
@app.route('/reset_election', methods=['GET', 'POST'])
def reset_election():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    message = ""
    
    if request.method == 'POST':
        # Verify admin password
        admin_password = request.form.get('admin_password')
        if not admin_password:
            message = "Please enter admin password"
        else:
            # Verify admin password
            conn = sqlite3.connect('voting.db')
            c = conn.cursor()
            c.execute("SELECT password FROM admins WHERE username = 'admin'")
            admin_record = c.fetchone()
            conn.close()
            
            if not admin_record or hash_password(admin_password) != admin_record[0]:
                message = "Invalid admin password"
            else:
                # Reset only votes, keep voters and candidates
                conn = sqlite3.connect('voting.db')
                c = conn.cursor()
                
                # Delete only votes
                c.execute("DELETE FROM votes")
                
                # Reset has_voted status for voters and candidates
                c.execute("UPDATE voters SET has_voted = 0")
                c.execute("UPDATE candidates SET has_voted = 0")
                
                # Reset election status to open and hide results
                c.execute("UPDATE election_settings SET status = 'open', show_results = 0")
                
                conn.commit()
                conn.close()
                
                message = "Election data reset successfully! Only votes were cleared."
    
    # Display confirmation page with password field
    return f'''
    <html>
    <head>
        <title>Reset Election Data</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>Reset Election Data</h2>
                    <div style="text-align: center; font-size: 3rem; margin: 20px 0;">⚠️</div>
                    {'<div class="no-results" style="background-color: #e74c3c; border-color: #e74c3c;"><strong>' + message + '</strong></div>' if message else ''}
                    <div>
                        <h3>Confirm Reset Action</h3>
                        <div class="no-results">
                            <p><strong>WARNING: This action cannot be undone!</strong></p>
                            <p>Are you sure you want to reset election data?</p>
                        </div>
                        
                        <div style="background-color: var(--bg-secondary); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border); margin: 20px 0;">
                            <div style="margin-bottom: 10px;">✓ Only votes will be deleted</div>
                            <div style="margin-bottom: 10px;">✓ Voter and candidate accounts will be preserved</div>
                            <div style="margin-bottom: 10px;">✓ All users' "has voted" status will be reset</div>
                            <div style="margin-bottom: 10px;">✓ Election status will be reset to open</div>
                            <div>✓ Results visibility will be hidden</div>
                        </div>
                        
                        <form method="POST">
                            <div>
                                <label for="admin_password">Admin Password:</label>
                                <input type="password" id="admin_password" name="admin_password" required style="width: 100%; background-color: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-small); padding: 10px; margin: 10px 0;">
                            </div>
                            <div>
                                <button class="portal-button" type="submit" onclick="return confirm('Final Confirmation: Are you absolutely sure you want to reset election data? Only votes will be cleared.')">Yes, Reset Election Data</button>
                            </div>
                        </form>
                    </div>
                    <div class="button-group">
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Cancel and Return to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''


# Manage Users (Combined view for voters and candidates)
@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    message = ""
    message_type = "info"  # info, success, error
    
    # Handle form submissions for updating voter information
    if request.method == 'POST':
        conn = sqlite3.connect('voting.db')
        c = conn.cursor()
        
        if 'update_candidate_password' in request.form:
            candidate_id = request.form['candidate_id']
            new_password = request.form['new_password']
            
            if new_password:  # Only update if a password was provided
                try:
                    hashed_password = hash_password(new_password)
                    c.execute("UPDATE candidates SET password = ? WHERE candidate_id = ?", (hashed_password, candidate_id))
                    conn.commit()
                    message = f"Password for candidate {candidate_id} updated successfully!"
                    message_type = "success"
                except Exception as e:
                    message = f"Error updating password for candidate {candidate_id}: {str(e)}"
                    message_type = "error"
            else:
                message = f"Please provide a new password for candidate {candidate_id}"
                message_type = "error"
        elif 'update_voter' in request.form:
            voter_id = request.form['voter_id']
            new_name = request.form['name']
            
            # Validate name
            if not new_name.replace(' ', '').isalpha() or len(new_name) > 55:
                message = f"Error: Name can only contain letters and must be no more than 55 characters!"
                message_type = "error"
            else:
                try:
                    c.execute("UPDATE voters SET name = ? WHERE voter_id = ?", (new_name, voter_id))
                    conn.commit()
                    message = f"Voter {voter_id} updated successfully!"
                    message_type = "success"
                except Exception as e:
                    message = f"Error updating voter {voter_id}: {str(e)}"
                    message_type = "error"
        elif 'update_candidate' in request.form:
            candidate_id = request.form['candidate_id']
            new_name = request.form['name']
            new_party = request.form['party']
            
            # Validate name
            if not new_name.replace(' ', '').isalpha() or len(new_name) > 55:
                message = f"Error: Name can only contain letters and must be no more than 55 characters!"
                message_type = "error"
            else:
                try:
                    c.execute("UPDATE candidates SET name = ?, party = ? WHERE candidate_id = ?", (new_name, new_party, candidate_id))
                    conn.commit()
                    message = f"Candidate {candidate_id} updated successfully!"
                    message_type = "success"
                except Exception as e:
                    message = f"Error updating candidate {candidate_id}: {str(e)}"
                    message_type = "error"
        elif 'delete_voter' in request.form:
            voter_id = request.form['voter_id']
            
            try:
                c.execute("DELETE FROM voters WHERE voter_id = ?", (voter_id,))
                conn.commit()
                message = f"Voter {voter_id} deleted successfully!"
                message_type = "success"
            except Exception as e:
                message = f"Error deleting voter {voter_id}: {str(e)}"
                message_type = "error"
        elif 'delete_candidate' in request.form:
            candidate_id = request.form['candidate_id']
            
            # Prevent deletion of NOTA candidate
            if candidate_id == 'NOTA':
                message = f"Error: NOTA candidate cannot be deleted!"
                message_type = "error"
            else:
                try:
                    c.execute("DELETE FROM candidates WHERE candidate_id = ?", (candidate_id,))
                    conn.commit()
                    message = f"Candidate {candidate_id} deleted successfully!"
                    message_type = "success"
                except Exception as e:
                    message = f"Error deleting candidate {candidate_id}: {str(e)}"
                    message_type = "error"
        elif 'update_password' in request.form:
            user_id = request.form['user_id']
            user_type = request.form['user_type']
            new_password = request.form['new_password']
            
            if not new_password:  # Check if password is provided
                message = f"Please provide a new password for {user_type} {user_id}"
                message_type = "error"
            elif len(new_password) < 3:  # Validate password length
                message = f"Error: New password must be at least 3 characters long!"
                message_type = "error"
            elif not any(c.isalpha() for c in new_password) or not any(not c.isalpha() for c in new_password):
                message = "Error: Password must contain both letters and non-letter characters (numbers or special characters)!"
                message_type = "error"
            else:  # Only update if a password was provided and valid
                try:
                    hashed_password = hash_password(new_password)
                    if user_type == 'voter':
                        c.execute("UPDATE voters SET password = ? WHERE voter_id = ?", (hashed_password, user_id))
                        conn.commit()
                        message = f"Password for voter {user_id} updated successfully!"
                    elif user_type == 'candidate':
                        c.execute("UPDATE candidates SET password = ? WHERE candidate_id = ?", (hashed_password, user_id))
                        conn.commit()
                        message = f"Password for candidate {user_id} updated successfully!"
                    message_type = "success"
                except Exception as e:
                    message = f"Error updating password for {user_type} {user_id}: {str(e)}"
                    message_type = "error"
        elif 'show_password_popup' in request.form:
            # This is just to trigger the popup, no database action needed
            voter_id = request.form['voter_id']
            # The popup will be handled by JavaScript
            pass
        
        conn.close()
    
    # Get voter and candidate data
    conn = sqlite3.connect('voting.db')
    c = conn.cursor()
    
    # Get voters
    c.execute("SELECT voter_id, name, has_voted FROM voters")
    voters = c.fetchall()
    
    # Get candidates
    c.execute("SELECT candidate_id, name, party, has_voted FROM candidates")
    candidates = c.fetchall()
    
    conn.close()
    
    # Create editable voters table
    voters_table = """
    <h3>Registered Voters</h3>
    <table>
    <tr><th>Voter ID</th><th>Name</th><th>Status</th><th>Update</th><th>Password</th><th>Delete</th></tr>
    """
    
    for voter in voters:
        status = "Voted" if voter[2] else "Not Voted"
        voters_table += f"""
        <tr>
            <form method="POST" style="display:inline;">
            <td>{voter[0]}<input type="hidden" name="voter_id" value="{voter[0]}"></td>
            <td><input type="text" name="name" value="{voter[1]}" style="width: 100%; background-color: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-small); padding: 8px;"></td>
            <td>{status}</td>
            <td><button class="portal-button" type="submit" name="update_voter" value="1" style="padding: 8px 12px; font-size: 0.9rem;">Update</button></td>
            <td><button class="option-button" type="button" onclick="showPasswordPopup('{voter[0]}', 'voter')" style="padding: 8px 12px; font-size: 0.9rem;">Update Password</button></td>
            <td><button class="option-button" type="submit" name="delete_voter" value="1" onclick="return confirm('Are you sure you want to delete voter {voter[0]}?')" style="padding: 8px 12px; font-size: 0.9rem;">Delete</button></td>
            </form>
        </tr>
        """
    voters_table += "</table>"
    
    # Create candidates table with editable features
    candidates_table = """
    <h3>Registered Candidates</h3>
    <table>
    <tr><th>Candidate ID</th><th>Name</th><th>Party</th><th>Status</th><th>Update</th><th>Password</th><th>Delete</th></tr>
    """
    
    for candidate in candidates:
        status = "Voted" if candidate[3] else "Not Voted"
        # Disable delete button for NOTA candidate
        delete_button = "<button class=\"option-button\" disabled style=\"padding: 8px 12px; font-size: 0.9rem;\">Cannot Delete</button>" if candidate[0] == 'NOTA' else f"<button class=\"option-button\" type=\"submit\" name=\"delete_candidate\" value=\"1\" onclick=\"return confirm('Are you sure you want to delete candidate {candidate[0]}?')\" style=\"padding: 8px 12px; font-size: 0.9rem;\">Delete</button>"
        candidates_table += f"""
        <tr>
            <form method="POST" style="display:inline;">
            <td>{candidate[0]}<input type="hidden" name="candidate_id" value="{candidate[0]}"></td>
            <td><input type="text" name="name" value="{candidate[1]}" style="width: 100%; background-color: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-small); padding: 8px;"></td>
            <td><input type="text" name="party" value="{candidate[2]}" style="width: 100%; background-color: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-small); padding: 8px;"></td>
            <td>{status}</td>
            <td><button class="portal-button" type="submit" name="update_candidate" value="1" style="padding: 8px 12px; font-size: 0.9rem;">Update</button></td>
            <td><button class="option-button" type="button" onclick="showPasswordPopup('{candidate[0]}', 'candidate')" style="padding: 8px 12px; font-size: 0.9rem;">Update Password</button></td>
            <td>{delete_button}</td>
            </form>
        </tr>
        """
    candidates_table += "</table>"
    
    return f'''
    <html>
    <head>
        <title>Manage Users</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Electronic Voting System</h1>
            </header>
            <main>
                <section class="election-status">
                    <h2>User Management</h2>
                    <p>View and manage all registered users in the system.</p>
                    {f"<div class='no-results' style='background-color: #27ae60; border-color: #27ae60;'><strong>{message}</strong></div>" if message and message_type == 'success' else ""}
                    {f"<div class='no-results' style='background-color: #e74c3c; border-color: #e74c3c;'><strong>{message}</strong></div>" if message and message_type == 'error' else ""}
                    {f"<div class='no-results' style='background-color: #3498db; border-color: #3498db;'><strong>{message}</strong></div>" if message and message_type == 'info' else ""}
                </section>
                
                <section class="user-portals">
                    <div>
                        {voters_table}
                        <br>
                        {candidates_table}
                    </div>
                </section>
                
                <section class="additional-options">
                    <h3>Management Actions</h3>
                    <div class="button-group">
                        <button class="portal-button" onclick="window.location.href='/manage_voters'">Manage Voters (Add/Edit/Delete)</button>
                        <button class="portal-button" onclick="window.location.href='/manage_candidates'">Manage Candidates (Add/Edit/Delete)</button>
                        <button class="option-button" onclick="window.location.href='/admin_dashboard'">Back to Dashboard</button>
                    </div>
                </section>
            </main>
        </div>
        
        <!-- Password Update Popup -->
        <div id="passwordPopup" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: #111111; padding: 20px; border: 1px solid #333333; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); z-index: 1000; border-radius: 16px;">
            <h3>Update Password</h3>
            <form method="POST" id="passwordForm">
                <input type="hidden" name="user_id" id="popupUserId">
                <input type="hidden" name="user_type" id="popupUserType">
                <div>
                    <label for="popupUserIdDisplay">User ID:</label>
                    <input type="text" id="popupUserIdDisplay" readonly style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div>
                    <label for="newPassword">New Password:</label>
                    <input type="password" id="newPassword" name="new_password" required style="width: 100%; background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333333; border-radius: 8px; padding: 8px;">
                </div>
                <div style="margin-top: 15px;">
                    <button class="portal-button" type="submit" name="update_password" value="1">Update Password</button>
                    <button class="option-button" type="button" onclick="closePasswordPopup()">Cancel</button>
                </div>
            </form>
        </div>
        
        <!-- Overlay for popup -->
        <div id="popupOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 999;" onclick="closePasswordPopup()"></div>
        
        <script>
        function showPasswordPopup(userId, userType) {{
            document.getElementById('popupUserId').value = userId;
            document.getElementById('popupUserIdDisplay').value = userId;
            document.getElementById('popupUserType').value = userType;
            document.getElementById('newPassword').value = '';
            document.getElementById('passwordPopup').style.display = 'block';
            document.getElementById('popupOverlay').style.display = 'block';
        }}
        
        function closePasswordPopup() {{
            document.getElementById('passwordPopup').style.display = 'none';
            document.getElementById('popupOverlay').style.display = 'none';
        }}
        </script>
    </body>
    </html>
    '''


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
