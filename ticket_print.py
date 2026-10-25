import sys
import os
import html
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

def generate_html(task: str, priority: str) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    task = html.escape(task).replace("\n", "<br>")

    priority_text = "Faible"
    if priority == "⚡️⚡️":
        priority_text = "Moyen"
    elif priority == "⚡️⚡️⚡️":
        priority_text = "Élevé"

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
  .priority-wrapper {{
    border: 2px solid #444;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 20px;
  }}
  .priority-text {{
    font-size:1.4rem; font-weight:800;
  }}
  .task-wrapper {{
    word-wrap: break-word;
    text-align: center;
    white-space: normal;
    font-size:2.3rem; font-weight:800; margin:28px 0;
    padding: 0 10px;
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
    
    <div class="priority-wrapper">
      <div class="priority-text">Priorité : {priority_text}</div>
    </div>

    <div class="task-wrapper">
      {task}
    </div>
    <div class="footer">🔔 N’oublie pas de la réaliser.</div>
  </div>
</body>
</html>"""

def generate_message_html(message: str, sender: str) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    message = html.escape(message).replace("\n", "<br>")
    sender = html.escape(sender)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<style>
  body {{
    background:#fff; margin:0;
    display:flex; justify-content:center; padding:20px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }}
  #ticket {{
    width:{PAPER_WIDTH}px; background:#fff; padding:28px; text-align:center;
  }}
  .title {{
    font-size:1.9rem; font-weight:900; margin:0 0 6px;
  }}
  .from {{
    font-size:1.5rem; margin:0 0 4px;
  }}
  .from b {{ font-weight:900; }}
  .date {{
    font-size:1.1rem; color:#444;
  }}
  .dashed {{
    border-top: 3px dashed #444; margin:22px 0;
  }}
  .message {{
    word-wrap: break-word; white-space: normal;
    font-size:1.8rem; font-weight:600; line-height:1.35;
    text-align:left; padding: 0 6px;
  }}
  .quote {{
    font-size:4rem; font-weight:900; line-height:1; height:2.2rem;
  }}
  .signature {{
    text-align:right; font-size:1.5rem; font-style:italic; margin-top:18px; padding: 0 6px;
  }}
  .footer {{
    font-size:1.2rem; color:#666; margin-top:8px;
  }}
</style>
</head>
<body>
  <div id="ticket">
    <div class="title">💌 Nouveau message</div>
    <div class="from">de <b>{sender}</b></div>
    <div class="date">📅 Reçu le : {now}</div>

    <div class="dashed"></div>
    <div class="quote">“</div>
    <div class="message">{message}</div>
    <div class="signature">— {sender}</div>
    <div class="dashed"></div>

    <div class="footer">✉️ Envoyé depuis ton IMP</div>
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
    p = Network(PRINTER_IP)
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
    task = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    priority = os.environ.get("PRIORITY", "⚡️")
    ticket_type = os.environ.get("TICKET_TYPE", "task")

    if not task:
        task = input("Entrez la tâche à imprimer : ").strip()
        if not task:
            print("❌ Aucune tâche fournie.")
            return

    if ticket_type == "message":
        content = generate_message_html(task, os.environ.get("SENDER", "Anonyme"))
    else:
        content = generate_html(task, priority)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
        html_path = tmp_html.name
        tmp_html.write(content.encode("utf-8"))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_png:
        png_path = tmp_png.name

    try:
        render_to_png(html_path, png_path, PAPER_WIDTH)
        im = Image.open(png_path)
        im = trim(im)
        if im.size[0] != PAPER_WIDTH:
            ratio = PAPER_WIDTH / float(im.size[0])
            im = im.resize((PAPER_WIDTH, int(im.size[1] * ratio)), Image.LANCZOS)
        im.save(png_path)

        print_png(png_path)
        print("✅ Ticket imprimé.")
    finally:
        for f in (html_path, png_path):
            try:
                os.remove(f)
            except Exception:
                pass

if __name__ == "__main__":
    main()