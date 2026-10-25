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

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

def date_fr(d: datetime) -> str:
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"

def fit_size(text: str, sizes) -> int:
    """Taille de police selon la longueur du texte : [(longueur max, taille), ...]."""
    for max_len, size in sizes:
        if len(text) <= max_len:
            return size
    return sizes[-1][1]

def as_html(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")

# Styles communs aux deux tickets : noir pur sur blanc, pas de gris (rendu thermique)
BASE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;900&family=JetBrains+Mono:wght@500;700&family=Caveat:wght@700&display=block');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background:#fff; color:#000; font-family: 'Inter', 'Liberation Sans', sans-serif; }}
#ticket {{ width:{PAPER_WIDTH}px; padding: 8px 6px 28px; }}
.mono {{ font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; }}
.caps {{ text-transform: uppercase; letter-spacing: .18em; }}
.band {{
  background:#000; color:#fff; border-radius: 14px;
  display:flex; align-items:center; gap:14px; padding: 18px 22px;
}}
.band svg {{ width:44px; height:44px; flex:0 0 auto; }}
.band .t {{ font-size: 2.3rem; font-weight: 900; letter-spacing: .06em; line-height: 1; flex:1; }}
.band .h {{ font-size: 1.5rem; font-weight: 700; }}
.date {{ font-size: 1.05rem; font-weight: 700; text-align:center; margin: 14px 0 0; }}
.dash {{ border-top: 3px dashed #000; margin: 22px 0; }}
.rule {{ border-top: 4px solid #000; margin: 22px 0; }}
"""

ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 12.5l3 3 5-6"/></svg>'
ICON_MAIL = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M3 6.5l9 6.5 9-6.5"/></svg>'
ICON_HEART = '<svg viewBox="0 0 24 24" width="18" height="18" fill="#000"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 5.3 3.1 1.7-1.9 3.2-3.1 5.3-3.1 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>'

def generate_html(task: str, priority: str) -> str:
    now = datetime.now()

    level = {"⚡️⚡️": 2, "⚡️⚡️⚡️": 3}.get(priority, 1)
    priority_text = {1: "Faible", 2: "Moyenne", 3: "Élevée"}[level]
    bars = "".join(
        f'<span class="bar{" on" if i < level else ""}" style="height:{14 + i * 9}px"></span>'
        for i in range(3)
    )
    size = fit_size(task, [(25, 50), (60, 42), (120, 34), (220, 28), (10**9, 24)])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<style>
{BASE_CSS}
.task {{
  font-size:{size}px; font-weight: 900; line-height: 1.12; letter-spacing: -.01em;
  word-wrap: break-word; overflow-wrap: anywhere; padding: 6px 4px;
}}
.prio {{ display:flex; align-items:center; gap: 14px; }}
.prio .lbl {{ font-size: 1.05rem; font-weight: 700; flex: 1; }}
.bars {{ display:flex; align-items:flex-end; gap: 5px; }}
.bar {{ width: 14px; border: 3px solid #000; border-radius: 3px; }}
.bar.on {{ background:#000; }}
.prio .val {{ font-size: 1.5rem; font-weight: 900; padding: 4px 12px; border: 3px solid #000; border-radius: 10px; }}
.prio .val.hot {{ background:#000; color:#fff; }}
.done {{ display:flex; align-items:center; gap: 14px; font-size: 1.15rem; font-weight: 700; }}
.box {{ width: 34px; height: 34px; border: 4px solid #000; border-radius: 7px; flex: 0 0 auto; }}
.done .line {{ flex:1; border-bottom: 3px dotted #000; height: 26px; }}
</style>
</head>
<body>
  <div id="ticket">
    <div class="band">
      {ICON_CHECK}
      <div class="t">À FAIRE</div>
      <div class="h mono">{now:%H:%M}</div>
    </div>
    <div class="date mono caps">{date_fr(now)}</div>

    <div class="dash"></div>
    <div class="task">{as_html(task)}</div>
    <div class="dash"></div>

    <div class="prio">
      <div class="lbl mono caps">Priorité</div>
      <div class="bars">{bars}</div>
      <div class="val{" hot" if level == 3 else ""}">{priority_text}</div>
    </div>

    <div class="rule"></div>
    <div class="done">
      <div class="box"></div>
      <div class="mono caps">Fait le</div>
      <div class="line"></div>
    </div>
  </div>
</body>
</html>"""

def generate_message_html(message: str, sender: str) -> str:
    now = datetime.now()
    size = fit_size(message, [(40, 40), (110, 34), (220, 29), (350, 25), (10**9, 22)])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<style>
{BASE_CSS}
.from {{ display:flex; align-items:center; gap: 14px; }}
.from .chip {{ background:#000; color:#fff; font-size: 1rem; font-weight: 700; padding: 6px 10px; border-radius: 8px; }}
.from .name {{ font-size: 2rem; font-weight: 900; line-height: 1.1; overflow-wrap: anywhere; }}
.quote {{ font-family: Georgia, 'DejaVu Serif', serif; font-size: 6rem; font-weight: 900; line-height: .6; height: 42px; }}
.message {{
  font-size:{size}px; font-weight: 700; line-height: 1.32;
  word-wrap: break-word; overflow-wrap: anywhere; padding: 0 4px;
}}
.sign {{ font-family: 'Caveat', cursive; font-size: 2.9rem; text-align: right; margin-top: 14px; padding-right: 6px; line-height: 1; overflow-wrap: anywhere; }}
.footer {{ display:flex; align-items:center; justify-content:center; gap: 8px; font-size: .95rem; font-weight: 700; }}
</style>
</head>
<body>
  <div id="ticket">
    <div class="band">
      {ICON_MAIL}
      <div class="t">MESSAGE</div>
      <div class="h mono">{now:%H:%M}</div>
    </div>
    <div class="date mono caps">{date_fr(now)}</div>

    <div class="rule"></div>
    <div class="from">
      <div class="chip mono caps">De</div>
      <div class="name">{html.escape(sender)}</div>
    </div>
    <div class="dash"></div>

    <div class="quote">“</div>
    <div class="message">{as_html(message)}</div>
    <div class="sign">— {html.escape(sender)}</div>

    <div class="rule"></div>
    <div class="footer mono caps">Envoyé avec {ICON_HEART} pour toi</div>
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