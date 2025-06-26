from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
import requests
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = 'this-is-a-secret'  # Session key
report_buffer = BytesIO()

def check_status(url):
    try:
        response = requests.get(url, timeout=5)
        code = response.status_code
        if code == 200:
            return code, "✅ Site is Live"
        elif code == 404:
            return code, "❌ 404 Not Found"
        elif 500 <= code < 600:
            return code, "⚠️ Server Error"
        else:
            return code, f"⚠️ HTTP {code}"
    except requests.exceptions.RequestException:
        return None, "❌ Could not connect"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    global report_buffer
    file = request.files['file']
    if not file:
        return "No file uploaded", 400

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return "Unsupported file format. Please upload CSV or XLSX.", 400

        if 'domain' not in df.columns:
            return "Missing 'domain' column in file.", 400

        status_codes = []
        messages = []

        for url in df['domain']:
            code, message = check_status(str(url).strip())
            status_codes.append(code)
            messages.append(message)

        df['status_code'] = status_codes
        df['message'] = messages

        # Save to buffer
        report_buffer = BytesIO()
        df.to_excel(report_buffer, index=False)
        report_buffer.seek(0)

        # Store in session
        session['results'] = df.to_dict(orient='records')
        return redirect(url_for('results'))

    except Exception as e:
        return f"Error processing file: {str(e)}", 500

@app.route('/results')
def results():
    data = session.get('results', [])
    return render_template('results.html', results=data)

@app.route('/check-url', methods=['POST'])
def check_url():
    new_url = request.form.get('url')
    if not new_url:
        return redirect(url_for('results'))

    code, message = check_status(new_url.strip())

    # Append to session results
    new_entry = {
        'domain': new_url,
        'status_code': code,
        'message': message
    }

    results = session.get('results', [])
    results.clear()
    results.append(new_entry)
    session['results'] = results

    return redirect(url_for('results'))

@app.route('/download')
def download():
    global report_buffer
    report_buffer.seek(0)
    return send_file(
        report_buffer,
        download_name="results.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

