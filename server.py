from flask import Flask, request, jsonify, render_template, session
import hmac
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Secrets fournis par le service systemd (jamais dans le dépôt Git)
# Sans TASK_PASSWORD, le mode "Tâches à faire" reste verrouillé.
TASK_PASSWORD = os.environ.get("TASK_PASSWORD", "")

MAX_NAME_LEN = 40
MAX_MESSAGE_LEN = 500
MAX_TASK_LEN = 300

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

def launch_print(text: str, extra_env: dict):
    subprocess.Popen(
        ["python3", "ticket_print.py", text],
        cwd=BASE_DIR,
        env={**os.environ, **extra_env},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", tasks_unlocked=bool(session.get("tasks_ok")))

@app.route("/unlock", methods=["POST"])
def unlock():
    password = request.form.get("password", "")
    if TASK_PASSWORD and hmac.compare_digest(password.encode(), TASK_PASSWORD.encode()):
        session["tasks_ok"] = True
        session.permanent = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Mot de passe incorrect."}), 401

@app.route("/print", methods=["POST"])
def print_task():
    if not session.get("tasks_ok"):
        return jsonify({"status": "error", "message": "Accès refusé : mot de passe requis."}), 403
    task = (request.form.get("task") or "").strip()[:MAX_TASK_LEN]
    priority = request.form.get("priority")
    if task and priority:
        try:
            launch_print(task, {"TICKET_TYPE": "task", "PRIORITY": priority})
            return jsonify({"status": "success", "message": "Ticket imprimé avec succès !"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Aucune tâche ou priorité fournie."}), 400

@app.route("/message", methods=["POST"])
def print_message():
    name = (request.form.get("name") or "").strip()
    message = (request.form.get("message") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Indique ton nom pour envoyer un message."}), 400
    if not message:
        return jsonify({"status": "error", "message": "Ton message est vide."}), 400
    if len(name) > MAX_NAME_LEN or len(message) > MAX_MESSAGE_LEN:
        return jsonify({"status": "error", "message": "Message ou nom trop long."}), 400
    try:
        launch_print(message, {"TICKET_TYPE": "message", "SENDER": name})
        return jsonify({"status": "success", "message": "Message envoyé !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
