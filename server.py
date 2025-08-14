from flask import Flask, request, jsonify, render_template
import subprocess

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/print", methods=["POST"])
def print_task():
    task = request.form.get("task")
    if task:
        try:
            subprocess.Popen(["python3", "ticket_print.py", task])
            return jsonify({"status": "success", "message": "Ticket imprimé avec succès !"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Aucune tâche fournie."}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)