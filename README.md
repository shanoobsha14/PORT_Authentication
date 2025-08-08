# PORT_Authentication
Port Authentication (Flask App)

A simple Flask-based web app to **enable or disable USB ports** on Windows using PowerShell commands.

## Features

- 🔐 Login system (default: admin / password123)
- 🖥️ Dashboard to:
  - View current USB status
  - Enable/Disable all USB devices (except system ones)
- ⚠️ Admin privilege check
- ✅ Flash messages for feedback

## Requirements

- Windows OS
- Python 3.x
- Flask (`pip install Flask`)
- Run as Administrator

## How to Run

python app.py

Then visit: http://localhost:5000
File Structure

app.py                 # Main Flask app
templates/
├── index.html         # Login page
└── dashboard.html     # USB control dashboard

Warning

Use with caution. Disabling all USB ports may disable critical devices (e.g., keyboard/mouse).
