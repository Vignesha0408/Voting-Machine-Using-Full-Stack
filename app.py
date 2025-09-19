from flask import Flask, request, redirect, url_for, session, render_template_string
import random

app = Flask(__name__)
app.secret_key = 'some_secret_key'  # Needed for session management

# Store candidates and votes in memory
candidates = []
votes = {}
total_votes_needed = 0
result_password = 'SDMIT'  # Password to access results
captcha_value = ''  # CAPTCHA value for validation






# Admin login
@app.route('/', methods=['GET', 'POST'])
def admin_authentication():
    global result_password
    error_message = ''
    if request.method == 'POST':
        input_password = request.form['password']
        if input_password == result_password:
            return redirect(url_for('setup_candidates'))
        else:
            error_message = 'Incorrect password. Please try again.'
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voting Machine - Admin Login</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                width: 100%;
                max-width: 400px;
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 2rem;
                font-size: 2rem;
            }}
            .form-group {{
                margin-bottom: 1.5rem;
                text-align: left;
            }}
            label {{
                display: block;
                margin-bottom: 0.5rem;
                color: #555;
                font-weight: 500;
            }}
            input[type="password"] {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                transition: border-color 0.3s;
            }}
            input[type="password"]:focus {{
                outline: none;
                border-color: #667eea;
            }}
            .btn {{
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
            }}
            .error {{
                color: #e74c3c;
                margin-bottom: 1rem;
                padding: 10px;
                background: #ffeaea;
                border-radius: 5px;
                border: 1px solid #e74c3c;
            }}
            .voting-icon {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="voting-icon">🗳️</div>
            <h1>Voting Machine</h1>
            <p style="color: #666; margin-bottom: 2rem;">Admin Authentication Required</p>
            {f'<div class="error">{error_message}</div>' if error_message else ''}
            <form method="POST">
                <div class="form-group">
                    <label for="password">Enter Admin Password:</label>
                    <input type="password" name="password" id="password" required>
                </div>
                <button type="submit" class="btn">🔐 Login</button>
            </form>
        </div>
    </body>
    </html>
    '''

# Setup voting system (only accessible after admin login)
@app.route('/setup', methods=['GET', 'POST'])
def setup_candidates():
    if request.method == 'POST':
        num_candidates = int(request.form['num_candidates'])
        global candidates, votes, total_votes_needed
        candidates = [request.form[f'candidate_{i+1}'] for i in range(num_candidates)]
        votes = {candidate: 0 for candidate in candidates}
        total_votes_needed = int(request.form['total_votes_needed'])
        session['votes_cast'] = 0
        return redirect(url_for('vote'))

    # Setup form to enter candidates and voter count
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Setup Voting System</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
                padding: 2rem;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 2rem;
                font-size: 2.5rem;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #555;
                font-weight: 600;
                font-size: 1.1rem;
            }
            input[type="number"], input[type="text"] {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: all 0.3s;
            }
            input[type="number"]:focus, input[type="text"]:focus {
                outline: none;
                border-color: #f5576c;
                box-shadow: 0 0 0 3px rgba(245, 87, 108, 0.1);
            }
            .btn {
                padding: 12px 24px;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                margin: 0.5rem 0;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .btn-secondary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            #candidate_inputs {
                margin: 1rem 0;
                padding: 1rem;
                background: #f8f9fa;
                border-radius: 8px;
                border: 2px dashed #ddd;
                min-height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
            }
            .candidate-input {
                background: white;
                padding: 1rem;
                margin: 0.5rem 0;
                border-radius: 8px;
                border: 1px solid #eee;
            }
            .setup-icon {
                text-align: center;
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            .instructions {
                background: #e3f2fd;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 2rem;
                border-left: 4px solid #2196f3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="setup-icon">⚙️</div>
            <h1>Setup Voting System</h1>
            <div class="instructions">
                <strong>📋 Instructions:</strong>
                <ol style="margin-left: 1rem; margin-top: 0.5rem;">
                    <li>Enter the number of candidates</li>
                    <li>Click "Generate Candidate Inputs" to create input fields</li>
                    <li>Fill in candidate names</li>
                    <li>Set the total number of voters</li>
                    <li>Click "Start Voting" to begin</li>
                </ol>
            </div>
            <form method="POST">
                <div class="form-group">
                    <label for="num_candidates">📊 Number of Candidates:</label>
                    <input type="number" name="num_candidates" id="num_candidates" min="1" max="10" required>
                </div>
                
                <button type="button" class="btn btn-secondary" onclick="generateCandidateInputs()">🎯 Generate Candidate Inputs</button>
                
                <div id="candidate_inputs">
                    Click "Generate Candidate Inputs" to create input fields
                </div>
                
                <div class="form-group">
                    <label for="total_votes_needed">👥 Total Number of Voters:</label>
                    <input type="number" name="total_votes_needed" id="total_votes_needed" min="1" required>
                </div>
                
                <button type="submit" class="btn">🚀 Start Voting System</button>
            </form>
        </div>
        
        <script>
        function generateCandidateInputs() {
            const numCandidates = document.querySelector('input[name="num_candidates"]').value;
            const candidateInputsDiv = document.getElementById("candidate_inputs");
            
            if (!numCandidates || numCandidates < 1) {
                alert("Please enter a valid number of candidates first!");
                return;
            }
            
            candidateInputsDiv.innerHTML = "";
            for (let i = 1; i <= numCandidates; i++) {
                candidateInputsDiv.innerHTML += `
                    <div class="candidate-input">
                        <label for="candidate_${i}">🏆 Candidate ${i} Name:</label>
                        <input type="text" name="candidate_${i}" id="candidate_${i}" placeholder="Enter candidate name" required>
                    </div>
                `;
            }
        }
        </script>
    </body>
    </html>
    '''

# CAPTCHA generation
def generate_captcha():
    global captcha_value
    captcha_value = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=3))

# Vote casting
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    global captcha_value
    message = ''
    if request.method == 'POST':
        candidate = request.form['candidate']
        captcha_input = request.form['captcha']
        if captcha_input != captcha_value:
            message = 'Invalid CAPTCHA. Please try again.'
        else:
            if candidate in votes:
                votes[candidate] += 1
                session['votes_cast'] += 1
                message = 'Vote cast successfully!'

            # Check if voting is complete
            if session['votes_cast'] >= total_votes_needed:
                return redirect(url_for('enter_password'))

    # Voting form with CAPTCHA
    generate_captcha()
    votes_remaining = total_votes_needed - session.get('votes_cast', 0)
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cast Your Vote</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                min-height: 100vh;
                padding: 2rem;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 2rem;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin-bottom: 1rem;
                font-size: 2.5rem;
            }}
            .vote-info {{
                text-align: center;
                background: #e8f5e8;
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                border: 2px solid #4caf50;
            }}
            .candidates {{
                margin: 2rem 0;
            }}
            .candidate-option {{
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 1rem;
                margin: 1rem 0;
                transition: all 0.3s;
                cursor: pointer;
                position: relative;
            }}
            .candidate-option:hover {{
                border-color: #28a745;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .candidate-option input[type="radio"] {{
                position: absolute;
                opacity: 0;
            }}
            .candidate-option input[type="radio"]:checked + label {{
                background: #28a745;
                color: white;
            }}
            .candidate-option label {{
                display: block;
                padding: 1rem;
                border-radius: 8px;
                transition: all 0.3s;
                cursor: pointer;
                font-size: 1.1rem;
                font-weight: 500;
            }}
            .captcha-section {{
                background: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 10px;
                padding: 1.5rem;
                margin: 2rem 0;
                text-align: center;
            }}
            .captcha-display {{
                font-size: 2rem;
                font-weight: bold;
                letter-spacing: 0.5rem;
                background: #343a40;
                color: #ffc107;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                font-family: 'Courier New', monospace;
            }}
            input[type="text"] {{
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                text-align: center;
                width: 200px;
                margin: 0 1rem;
            }}
            input[type="text"]:focus {{
                outline: none;
                border-color: #28a745;
            }}
            .btn {{
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                margin-top: 1rem;
            }}
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
            .btn:disabled {{
                background: #6c757d;
                cursor: not-allowed;
                transform: none;
            }}
            .message {{
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                text-align: center;
                font-weight: 500;
            }}
            .message.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .message.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .vote-icon {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center;">
                <div class="vote-icon">🗳️</div>
                <h1>Cast Your Vote</h1>
            </div>
            
            <div class="vote-info">
                <strong>📊 Voting Progress:</strong> {session.get('votes_cast', 0)} of {total_votes_needed} votes cast<br>
                <strong>⏳ Remaining:</strong> {votes_remaining} votes
            </div>
            
            {f'<div class="message {"success" if "successfully" in message else "error"}">{message}</div>' if message else ''}
            
            <form method="POST" id="voteForm">
                <div class="candidates">
                    <h3 style="margin-bottom: 1rem; color: #333;">👥 Select a Candidate:</h3>
                    {''.join(f'''<div class="candidate-option">
                        <input type="radio" name="candidate" value="{candidate}" id="{candidate}">
                        <label for="{candidate}">🏆 {candidate}</label>
                    </div>''' for candidate in candidates)}
                </div>
                
                <div class="captcha-section">
                    <h3 style="margin-bottom: 1rem; color: #333;">🔒 Security Verification</h3>
                    <p>Please enter the CAPTCHA code below:</p>
                    <div class="captcha-display">{captcha_value}</div>
                    <input type="text" name="captcha" placeholder="Enter CAPTCHA" required>
                </div>
                
                <button type="submit" class="btn" id="submitBtn">✅ Submit Vote</button>
            </form>
        </div>
        
        <script>
        document.getElementById('voteForm').addEventListener('submit', function(e) {{
            const selectedCandidate = document.querySelector('input[name="candidate"]:checked');
            if (!selectedCandidate) {{
                e.preventDefault();
                alert('Please select a candidate before submitting your vote!');
                return;
            }}
            
            const captcha = document.querySelector('input[name="captcha"]').value;
            if (!captcha) {{
                e.preventDefault();
                alert('Please enter the CAPTCHA code!');
                return;
            }}
        }});
        
        // Add click handlers for candidate options
        document.querySelectorAll('.candidate-option').forEach(option => {{
            option.addEventListener('click', function() {{
                const radio = this.querySelector('input[type="radio"]');
                radio.checked = true;
            }});
        }});
        </script>
    </body>
    </html>
    '''

# Enter password to view results
@app.route('/enter_password', methods=['GET', 'POST'])
def enter_password():
    error_message = ''
    if request.method == 'POST':
        password = request.form['password']
        if password == result_password:
            return redirect(url_for('results'))
        else:
            error_message = 'Incorrect password. Please try again.'

    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Access Results</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 500px;
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 1rem;
                font-size: 2.5rem;
            }}
            .completion-message {{
                background: #d4edda;
                color: #155724;
                padding: 1.5rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                border: 2px solid #c3e6cb;
            }}
            .form-group {{
                margin-bottom: 2rem;
                text-align: left;
            }}
            label {{
                display: block;
                margin-bottom: 0.5rem;
                color: #555;
                font-weight: 600;
                font-size: 1.1rem;
            }}
            input[type="password"] {{
                width: 100%;
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 10px;
                font-size: 16px;
                transition: all 0.3s;
            }}
            input[type="password"]:focus {{
                outline: none;
                border-color: #ff9a9e;
                box-shadow: 0 0 0 3px rgba(255, 154, 158, 0.1);
            }}
            .btn {{
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }}
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
            .error {{
                color: #e74c3c;
                background: #ffeaea;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid #e74c3c;
            }}
            .results-icon {{
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            .voting-stats {{
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                border: 2px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="results-icon">🏆</div>
            <h1>Voting Complete!</h1>
            
            <div class="completion-message">
                <strong>✅ All votes have been successfully collected!</strong><br>
                Total votes cast: {session.get('votes_cast', 0)}
            </div>
            
            <div class="voting-stats">
                <h3 style="margin-bottom: 1rem; color: #333;">📊 Quick Stats</h3>
                <p><strong>Total Candidates:</strong> {len(candidates)}</p>
                <p><strong>Total Voters:</strong> {total_votes_needed}</p>
                <p><strong>Votes Collected:</strong> {session.get('votes_cast', 0)}</p>
            </div>
            
            {f'<div class="error">❌ {error_message}</div>' if error_message else ''}
            
            <form method="POST">
                <div class="form-group">
                    <label for="password">🔐 Enter Password to View Results:</label>
                    <input type="password" name="password" id="password" placeholder="Enter admin password" required>
                </div>
                <button type="submit" class="btn">📈 View Results</button>
            </form>
        </div>
    </body>
    </html>
    '''

# Display voting results with charts
@app.route('/results')
def results():
    labels = list(votes.keys())
    data = list(votes.values())
    total_votes_cast = sum(data)
    winner = max(votes.keys(), key=lambda x: votes[x]) if votes else "No votes cast"
    winner_votes = max(data) if data else 0

    # Calculate percentages
    percentages = [round((vote/total_votes_cast)*100, 1) if total_votes_cast > 0 else 0 for vote in data]

    # Display results and Chart.js for voting data
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voting Results - Final Report</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 2rem;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 2rem;
                font-size: 3rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .winner-announcement {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 2rem;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 3rem;
                box-shadow: 0 10px 30px rgba(40, 167, 69, 0.3);
            }
            .winner-announcement h2 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
            }
            .winner-announcement .winner-name {
                font-size: 3rem;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .results-summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 3rem;
            }
            .stat-card {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 1.5rem;
                border-radius: 10px;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            .stat-card h3 {
                color: #495057;
                margin-bottom: 0.5rem;
                font-size: 1rem;
            }
            .stat-card .stat-value {
                font-size: 2rem;
                font-weight: bold;
                color: #28a745;
            }
            .results-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 3rem;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .results-table th {
                background: linear-gradient(135deg, #495057 0%, #6c757d 100%);
                color: white;
                padding: 1rem;
                text-align: left;
                font-weight: 600;
            }
            .results-table td {
                padding: 1rem;
                border-bottom: 1px solid #dee2e6;
            }
            .results-table tr:nth-child(even) {
                background: #f8f9fa;
            }
            .results-table tr:hover {
                background: #e3f2fd;
                transition: background-color 0.3s;
            }
            .candidate-name {
                font-weight: 600;
                color: #333;
            }
            .vote-count {
                font-size: 1.2rem;
                font-weight: bold;
                color: #28a745;
            }
            .percentage {
                font-weight: 600;
                color: #6f42c1;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                transition: width 0.5s ease;
            }
            .charts-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }
            .chart-card {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }
            .chart-card h3 {
                text-align: center;
                margin-bottom: 1rem;
                color: #495057;
            }
            .chart-canvas {
                max-height: 400px;
            }
            .actions {
                text-align: center;
                margin-top: 2rem;
            }
            .btn {
                padding: 12px 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
                margin: 0 0.5rem;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .results-icon {
                text-align: center;
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            @media (max-width: 768px) {
                .charts-container {
                    grid-template-columns: 1fr;
                }
                h1 {
                    font-size: 2rem;
                }
                .winner-announcement h2 {
                    font-size: 1.8rem;
                }
                .winner-announcement .winner-name {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="results-icon">🏆</div>
            <h1>📊 Final Voting Results</h1>
            
            {% if winner != "No votes cast" %}
            <div class="winner-announcement">
                <h2>🎉 Winner Announcement</h2>
                <div class="winner-name">{{ winner }}</div>
                <p style="font-size: 1.2rem; margin-top: 1rem;">with {{ winner_votes }} votes ({{ percentages[labels.index(winner)] }}%)</p>
            </div>
            {% endif %}
            
            <div class="results-summary">
                <div class="stat-card">
                    <h3>📋 Total Candidates</h3>
                    <div class="stat-value">{{ labels|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>🗳️ Total Votes</h3>
                    <div class="stat-value">{{ total_votes_cast }}</div>
                </div>
                <div class="stat-card">
                    <h3>👥 Registered Voters</h3>
                    <div class="stat-value">{{ total_votes_needed }}</div>
                </div>
                <div class="stat-card">
                    <h3>📈 Turnout Rate</h3>
                    <div class="stat-value">{{ ((total_votes_cast/total_votes_needed)*100)|round(1) if total_votes_needed > 0 else 0 }}%</div>
                </div>
            </div>
            
            <h2 style="margin-bottom: 1rem; color: #333; text-align: center;">📋 Detailed Results</h2>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>🏅 Rank</th>
                        <th>👤 Candidate</th>
                        <th>🗳️ Votes</th>
                        <th>📊 Percentage</th>
                        <th>📈 Visual</th>
                    </tr>
                </thead>
                <tbody>
                    {% for candidate, vote_count, percentage in sorted_results %}
                    <tr>
                        <td><strong>{{ loop.index }}</strong></td>
                        <td class="candidate-name">{{ candidate }}</td>
                        <td class="vote-count">{{ vote_count }}</td>
                        <td class="percentage">{{ percentage }}%</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {{ percentage }}%"></div>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="charts-container">
                <div class="chart-card">
                    <h3>📊 Bar Chart</h3>
                    <canvas id="barChart" class="chart-canvas"></canvas>
                </div>
                <div class="chart-card">
                    <h3>🥧 Pie Chart</h3>
                    <canvas id="pieChart" class="chart-canvas"></canvas>
                </div>
            </div>
            
            <div class="actions">
                <a href="/" class="btn">🔄 Start New Election</a>
                <button onclick="window.print()" class="btn">🖨️ Print Results</button>
            </div>
        </div>
        
        <script>
        // Sort results for ranking
        const sortedResults = {{ sorted_results|tojsonfilter }};
        
        // Bar Chart
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: {{ labels|tojsonfilter }},
                datasets: [{
                    label: 'Votes',
                    data: {{ data|tojsonfilter }},
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const percentage = {{ percentages|tojsonfilter }}[context.dataIndex];
                                return `${context.parsed.y} votes (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        // Pie Chart
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {
            type: 'pie',
            data: {
                labels: {{ labels|tojsonfilter }},
                datasets: [{
                    data: {{ data|tojsonfilter }},
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const percentage = {{ percentages|tojsonfilter }}[context.dataIndex];
                                return `${context.label}: ${context.parsed} votes (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        </script>
    </body>
    </html>
    ''', votes=votes, labels=labels, data=data, total_votes_cast=total_votes_cast, 
         total_votes_needed=total_votes_needed, winner=winner, winner_votes=winner_votes,
         percentages=percentages, sorted_results=sorted(zip(labels, data, percentages), key=lambda x: x[1], reverse=True))

if __name__ == '__main__':
    app.run(debug=True)
