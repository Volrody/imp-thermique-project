import sys
import os
import tempfile
import subprocess
from datetime import datetime
from PIL import Image, ImageChops
from escpos.printer import Network

# —— CONFIG ——
PRINTER_IP = "192.168.4.71"   # <-- remplace par l’IP de ton imprimante
PAPER_WIDTH = 512              # largeur utile max (TM-T20III)
NODE_SCRIPT = "render_receipt.js"  # doit être présent dans le même dossier
# ————————————

def trim(im: Image.Image) -> Image.Image:
    """Rogne les bords blancs."""
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    return im.crop(bbox) if bbox else im

def generate_html(task: str) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body {{
    background:#fff;
    display:flex; justify-content:center; padding:20px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }}
  #ticket {{
    width:{PAPER_WIDTH}px; background:#fff; padding:28px; text-align:center;
  }}
  .title {{
    font-size:1.7rem; font-weight:900; margin:0 0 12px;
  }}
  .date-box {{
    font-size:1.2rem; color:#444;
    margin:20px 0;
    display:flex; flex-direction:column; align-items:center;
  }}
  .date-box .line {{
    width:100%; border-top: 2px solid #444; margin:6px 0;
  }}
  .task-wrapper {{
    word-wrap: break-word; /* Force le retour à la ligne automatique */
    text-align: center; /* Aligne le texte au centre */
    white-space: normal; /* S'assure que le retour à la ligne est normal */
    font-size:2.3rem; font-weight:800; margin:28px 0;
    padding: 0 10px; /* Ajoute un peu d'espace */
  }}
  .footer {{
    font-size:1.4rem; color:#666; margin-top:36px;
  }}
</style>
</head>
<body>
  <div id="ticket">
    <div class="title">🧾 Tâche à faire</div>

    <div class="date-box">
      <div class="line"></div>
      <div>📅 Créé le : {now}</div>
      <div class="line"></div>
    </div>

    <div class="task-wrapper">
      {task}
    </div>
    <div class="footer">🔔 N’oublie pas de la réaliser.</div>
  </div>
</body>
</html>"""

def render_to_png(html_path: str, out_path: str, width: int = PAPER_WIDTH):
    """Utilise Puppeteer (render_receipt.js) pour convertir HTML → PNG."""
    cmd = [
        "node", NODE_SCRIPT,
        "--html", html_path,
        "--out", out_path,
        "--width", str(width)
    ]
    subprocess.run(cmd, check=True)

def print_png(path_png: str):
    """Imprime l’image PNG sur l’imprimante réseau."""
    p = Network(PRINTER_IP)  # profil par défaut
    # Optionnel : informer la lib de la largeur utile si dispo
    try:
        p.profile.profile_data['media']['width']['pixel'] = PAPER_WIDTH
    except Exception:
        pass

    p.set(align="center")
    p.image(path_png)
    p.cut()
    try:
        p.close()
    except Exception:
        pass

def main():
    # Récupère la tâche depuis la ligne de commande (server.py l’envoie déjà comme ça)
    task = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if not task:
        task = input("Entrez la tâche à imprimer : ").strip()
        if not task:
            print("❌ Aucune tâche fournie.")
            return

    html = generate_html(task)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
        html_path = tmp_html.name
        tmp_html.write(html.encode("utf-8"))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_png:
        png_path = tmp_png.name

    try:
        # HTML -> PNG
        render_to_png(html_path, png_path, PAPER_WIDTH)

        # Rogner et s’assurer que la largeur = PAPER_WIDTH
        im = Image.open(png_path)
        im = trim(im)
        if im.size[0] != PAPER_WIDTH:
            ratio = PAPER_WIDTH / float(im.size[0])
            im = im.resize((PAPER_WIDTH, int(im.size[1] * ratio)), Image.LANCZOS)
        im.save(png_path)

        # Impression réseau
        print_png(png_path)
        print("✅ Ticket imprimé.")

    finally:
        # Nettoyage
        for f in (html_path, png_path):
            try:
                os.remove(f)
            except Exception:
                pass

if __name__ == "__main__":
    main()