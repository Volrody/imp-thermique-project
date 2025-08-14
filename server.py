from flask import Flask, request, redirect, render_template
import subprocess

app = Flask(__name__)  # utilise 'templates/' par défaut

PRINTER_IP = "192.168.4.71" # cette variable n'est pas utilisée ici, mais pas de problème

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/print", methods=["POST"])
def print_task():
    task = request.form.get("task")
    if task:
        # Lancer le script d'impression en arrière-plan.
        # Attention : si ton système est sous Windows, il faudra peut-être ajuster la commande.
        # Ici on utilise `Popen` pour ne pas bloquer le serveur en attendant la fin de l'impression.
        subprocess.Popen(["python3", "ticket_print.py", task])
    
    # Rediriger l'utilisateur vers la page principale après l'impression
    return redirect("/")

if __name__ == "__main__":
    # L'argument `debug=True` est super pour le développement, il redémarre le serveur
    # automatiquement quand tu modifies le code. Pense à le retirer en production.
    app.run(host="0.0.0.0", port=8080, debug=True)
