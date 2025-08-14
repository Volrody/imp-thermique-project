from flask import Flask, request, redirect, render_template
import subprocess

app = Flask(__name__)

# Remplace la ligne :
# subprocess.Popen(["python3", "ticket_print.py", task])

# Par cette nouvelle version :
@app.route("/print", methods=["POST"])
def print_task():
    task = request.form.get("task")
    if task:
        try:
            # Lancer le script d'impression en tant que sous-processus
            process = subprocess.run(
                ["python3", "ticket_print.py", task],
                capture_output=True, # Capturer la sortie standard et d'erreur
                text=True # Traiter la sortie comme du texte
            )
            # Afficher les sorties dans le journal du service
            print(f"Stdout du script d'impression: {process.stdout}")
            print(f"Stderr du script d'impression: {process.stderr}")
            
            # Gérer les erreurs de retour
            if process.returncode != 0:
                print("❌ Le script d'impression a échoué.")
        except Exception as e:
            print(f"❌ Erreur lors du lancement du script : {e}")

    return redirect("/")
