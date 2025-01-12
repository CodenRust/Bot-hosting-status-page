import os
import json
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Replace with a secure key in production

# Discord OAuth2 Config
DISCORD_CLIENT_ID = "1325410613111029830"
DISCORD_CLIENT_SECRET = "hP_0GU9uFXjLdWHlTStXUuXH9jfyA_xS"
DISCORD_REDIRECT_URI = "http://127.0.0.1:5000/callback"
DISCORD_API_BASE_URL = "https://discord.com/api"
DISCORD_AUTH_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

REPORTS_FILE = "reports.json"

# Ensure the reports.json file exists
if not os.path.exists(REPORTS_FILE):
    with open(REPORTS_FILE, "w") as f:
        json.dump([], f)  # Initialize with an empty list


def load_reports():
    """Load the reports from the JSON file."""
    try:
        with open(REPORTS_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Invalid format in reports.json; expected a list.")
            return data
    except (json.JSONDecodeError, ValueError, FileNotFoundError):
        with open(REPORTS_FILE, "w") as f:
            json.dump([], f)
        return []


def save_report(report):
    """Save a new report to the JSON file."""
    reports = load_reports()
    reports.append(report)
    with open(REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=4)


@app.route("/")
def index():
    """Render the main HTML page."""
    return render_template("status.html", logged_in="discord_user" in session)


@app.route("/login")
def login():
    """Redirect to Discord for authentication."""
    discord = OAuth2Session(DISCORD_CLIENT_ID, redirect_uri=DISCORD_REDIRECT_URI, scope=["identify"])
    authorization_url, state = discord.authorization_url(DISCORD_AUTH_URL)
    session["oauth2_state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    """Handle the OAuth2 callback from Discord."""
    discord = OAuth2Session(DISCORD_CLIENT_ID, state=session.get("oauth2_state"), redirect_uri=DISCORD_REDIRECT_URI)
    token = discord.fetch_token(DISCORD_TOKEN_URL, client_secret=DISCORD_CLIENT_SECRET, authorization_response=request.url)
    session["discord_token"] = token
    user_info = discord.get(f"{DISCORD_API_BASE_URL}/users/@me").json()
    session["discord_user"] = user_info
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Log out the user."""
    session.pop("discord_user", None)
    session.pop("discord_token", None)
    return redirect(url_for("index"))
# File to store service statuses
SERVICE_STATUSES_FILE = "service_statuses.json"

# Initialize the service statuses JSON if it doesn't exist
def initialize_service_statuses():
    if not os.path.exists(SERVICE_STATUSES_FILE):
        initial_statuses = {
            "fi9 Node": {"status": "Operational", "progress": 96, "icon": "check-circle", "color": "success"},
            "fi10 Node": {"status": "Operational", "progress": 96, "icon": "check-circle", "color": "success"},
            "us1 Node": {"status": "Operational", "progress": 96, "icon": "check-circle", "color": "success"},
            "us2 Node": {"status": "Operational", "progress": 96, "icon": "check-circle", "color": "success"},
            "us3 Node": {"status": "Operational", "progress": 96, "icon": "check-circle", "color": "success"}
        }
        with open(SERVICE_STATUSES_FILE, "w") as f:
            json.dump(initial_statuses, f, indent=4)

# Load service statuses from the JSON file
def load_service_statuses():
    try:
        with open(SERVICE_STATUSES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_service_statuses()
        return load_service_statuses()

# Save service statuses to the JSON file
def save_service_statuses(statuses):
    with open(SERVICE_STATUSES_FILE, "w") as f:
        json.dump(statuses, f, indent=4)

@app.route("/report", methods=["POST"])
def report_issue():
    """Handle issue reporting and update the service status globally."""
    if "discord_user" not in session:
        return jsonify({"error": "Unauthorized. Please log in with Discord."}), 401

    data = request.json
    if not data or "service_name" not in data or "title" not in data or "issue_details" not in data:
        return jsonify({"error": "Invalid data. Ensure `service_name`, `title`, and `issue_details` are provided."}), 400

    # Load service statuses from JSON
    service_statuses = load_service_statuses()

    # Update the service status if found
    if data["service_name"] in service_statuses:
        service_statuses[data["service_name"]]["status"] = "Critical Issue"
        service_statuses[data["service_name"]]["progress"] = 50
        service_statuses[data["service_name"]]["icon"] = "times-circle"
        service_statuses[data["service_name"]]["color"] = "danger"
        save_service_statuses(service_statuses)

    # Save the report to the reports.json
    discord_user = session["discord_user"]
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_user['id']}/{discord_user['avatar']}.png"
    report = {
        "service_name": data["service_name"],
        "title": data["title"],
        "issue_details": data["issue_details"],
        "reported_by": {
            "username": discord_user["username"],
            "id": discord_user["id"],
            "avatar_url": avatar_url,
        }
    }
    save_report(report)

    return jsonify({"message": "Issue reported successfully", "reported_issue": report, "statuses": service_statuses}), 200


@app.route("/status", methods=["GET"])
def get_status():
    """Fetch current service statuses."""
    service_statuses = load_service_statuses()
    transformed_statuses = {}

    for service, details in service_statuses.items():
        transformed_statuses[service] = {
            "icon": details["icon"],  # 'check-circle' or 'times-circle'
            "progress": details["progress"],  # e.g., 96
            "color": details["color"],  # 'success', 'danger', etc.
            "status_text": "Operational" if details["color"] == "success" else "Critical Issue"
        }
    return jsonify(transformed_statuses)




# Initialize the statuses when the server starts
initialize_service_statuses()





@app.route("/reports", methods=["GET"])
def get_reports():
    """Fetch all reported issues."""
    if "discord_user" not in session:
        return jsonify({"error": "Unauthorized. Please log in with Discord."}), 401
    reports = load_reports()
    return jsonify(reports)


if __name__ == "__main__":
    app.run(debug=True)
