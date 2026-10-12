"""
Genera dark_mode.svg y light_mode.svg estilo "neofetch" para el README del perfil de GitHub.
Corre localmente o desde GitHub Actions (ver .github/workflows/update-profile.yml).

Requisitos: pip install pillow requests
Variables de entorno opcionales: GH_TOKEN (para leer stats de GitHub)
"""
import datetime as dt
import os
import time
from pathlib import Path
from xml.sax.saxutils import escape

import requests

# ───────────────────────── CONFIGURA TUS DATOS AQUÍ ─────────────────────────
USERNAME = "RobertBenitez9805"
BIRTHDATE = dt.date(1998, 5, 6)        # fecha de nacimiento → "Uptime"
PHOTO = "photo.png"                     # foto con fondo transparente (o jpg con fondo liso)
ASCII_WIDTH = 46                        # columnas del retrato ASCII
KEEP_HEIGHT = 0.85                      # fracción vertical de la foto que se usa (desde arriba)

SECTIONS = [
    ("robertbenitez9805@github", [
        ("OS", "macOS, Fedora Linux"),
        ("Uptime", "{uptime}"),
        ("Host", "SnugZ USA"),
        ("Kernel", "Backend & Cloud Developer"),
        ("IDE", "Claude Code, VS Code"),
        None,
        ("Languages.Programming", "C#, Java, Python, SQL"),
        ("Languages.Cloud", "AWS Lambda, Step Functions, SQS"),
        ("Languages.Real", "Spanish, English"),
        ("Hobbies", "Spending time with family"),
    ]),
    ("Contact", [
        ("Email", "robertbs9805@gmail.com"),
        ("LinkedIn", "in/robert-benitez"),
    ]),
    ("GitHub Stats", "STATS"),
]
# ─────────────────────────────────────────────────────────────────────────────

COLS = 62            # ancho de la columna derecha en caracteres
FONT = 15
CHAR_W = FONT * 0.6  # ancho aprox. de un carácter monoespaciado
LINE_H = 20
PAD = 20

THEMES = {
    "dark":  dict(bg="#161b22", border="#30363d", text="#c9d1d9", key="#ffa657",
                  value="#a5d6ff", dots="#616e7f", add="#3fb950", dele="#f85149"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", text="#24292f", key="#953800",
                  value="#0a3069", dots="#a0a0a0", add="#1a7f37", dele="#cf222e"),
}


# ─────────────── Datos dinámicos ───────────────
def uptime() -> str:
    today = dt.date.today()
    y, m, d = today.year - BIRTHDATE.year, today.month - BIRTHDATE.month, today.day - BIRTHDATE.day
    if d < 0:
        m -= 1
        prev = today.replace(day=1) - dt.timedelta(days=1)
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"


def gh_stats() -> dict:
    token = os.getenv("GH_TOKEN")
    empty = dict(repos="?", contrib="?", stars="?", commits="?", followers="?",
                 loc="?", add="?", dele="?")
    if not token or USERNAME.startswith("TU_"):
        return empty
    h = {"Authorization": f"bearer {token}"}
    q = """query($login:String!,$after:String){ user(login:$login){
        followers{totalCount}
        repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST]){totalCount}
        repositories(first:100,after:$after,ownerAffiliations:OWNER,isFork:false){
          totalCount pageInfo{hasNextPage endCursor}
          nodes{name stargazerCount}}}}"""
    repos, after, user = [], None, None
    while True:
        r = requests.post("https://api.github.com/graphql", headers=h,
                          json={"query": q, "variables": {"login": USERNAME, "after": after}})
        data = r.json()
        if "data" not in data:
            raise RuntimeError(data)
        user = data["data"]["user"]
        page = user["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    commits = requests.get("https://api.github.com/search/commits",
                           params={"q": f"author:{USERNAME}"}, headers=h).json().get("total_count", 0)

    add = dele = 0
    for repo in repos:
        url = f"https://api.github.com/repos/{USERNAME}/{repo['name']}/stats/contributors"
        for _ in range(5):  # GitHub responde 202 mientras calcula
            r = requests.get(url, headers=h)
            if r.status_code != 202:
                break
            time.sleep(3)
        if r.status_code == 200 and isinstance(r.json(), list):
            for c in r.json():
                if c.get("author") and c["author"]["login"].lower() == USERNAME.lower():
                    add += sum(w["a"] for w in c["weeks"])
                    dele += sum(w["d"] for w in c["weeks"])

    f = lambda n: f"{n:,}"
    return dict(repos=f(len(repos)), contrib=f(user["repositoriesContributedTo"]["totalCount"]),
                stars=f(sum(x["stargazerCount"] for x in repos)), commits=f(commits),
                followers=f(user["followers"]["totalCount"]),
                loc=f(add - dele), add=f(add) + "++", dele=f(dele) + "--")


# ─────────────── Retrato ASCII ───────────────
def ascii_portrait(dark: bool) -> list[str]:
    """Convierte la foto en ASCII. Si es un PNG con fondo transparente, el fondo queda vacío."""
    if not Path(PHOTO).exists():
        return ["(pon tu foto junto", " a generate.py)"]
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
    im = Image.open(PHOTO).convert("RGBA")
    alpha = im.split()[3].point(lambda v: 255 if v > 128 else 0)
    if alpha.getbbox():
        l, t, r, b = alpha.getbbox()
        box = (l, t, r, t + int((b - t) * KEEP_HEIGHT))   # corta parte de los hombros
        im, alpha = im.crop(box), alpha.crop(box)
    gray = ImageOps.grayscale(im.convert("RGB"))
    # contraste calculado sobre la zona de la cara (elipse central-superior)
    w, h0 = gray.size
    face = Image.new("L", gray.size, 0)
    ImageDraw.Draw(face).ellipse((w * 0.18, h0 * 0.05, w * 0.85, h0 * 0.8), fill=255)
    gray = ImageOps.autocontrast(gray, cutoff=2, mask=ImageChops.multiply(face, alpha))
    gray = gray.filter(ImageFilter.SHARPEN)
    h = int(gray.height / gray.width * ASCII_WIDTH * 0.47)  # caracteres ~2x más altos que anchos
    gray = gray.resize((ASCII_WIDTH, h), Image.LANCZOS)
    alpha = alpha.resize((ASCII_WIDTH, h))
    ramp = "@%#*+=-:. "   # oscuro → denso, claro → liviano
    lines = []
    for y in range(h):
        row = ""
        for x in range(ASCII_WIDTH):
            if alpha.getpixel((x, y)) < 128:
                row += " "
            else:
                row += ramp[min(len(ramp) - 1, gray.getpixel((x, y)) * len(ramp) // 256)]
        lines.append(row.rstrip())
    return lines


# ─────────────── Render SVG ───────────────
def tspan(text, color, extra=""):
    return f'<tspan fill="{color}"{extra}>{escape(text)}</tspan>'


def kv_line(key, value, c, width=COLS):
    dots = width - len(key) - 2 - len(value) - 1
    return (tspan(key, c["key"]) + tspan(":", c["text"]) + " "
            + tspan("." * max(dots, 1), c["dots"]) + " " + tspan(value, c["value"]))


def header_line(title, c, first):
    prefix = "" if first else "— "
    rule = "—" * (COLS - len(prefix) - len(title) - 1)
    return tspan(prefix + title, c["value"]) + " " + tspan(rule, c["dots"])


def stats_lines(s, c):
    half = COLS // 2 - 1
    def pair(k1, v1, k2, v2):
        return kv_line(k1, v1, c, half) + tspan(" | ", c["dots"]) + kv_line(k2, v2, c, COLS - half - 3)
    return [
        pair("Repos", f"{s['repos']} {{Contributed: {s['contrib']}}}", "Stars", s["stars"]),
        pair("Commits", s["commits"], "Followers", s["followers"]),
        tspan("Lines of Code", c["key"]) + tspan(": ", c["text"]) + tspan(s["loc"], c["value"])
        + tspan(" ( ", c["text"]) + tspan(s["add"], c["add"]) + tspan(", ", c["text"])
        + tspan(s["dele"], c["dele"]) + tspan(" )", c["text"]),
    ]


def render(theme: str, stats: dict, up: str) -> str:
    c = THEMES[theme]
    right = []
    for i, (title, items) in enumerate(SECTIONS):
        if i:
            right.append("")
        right.append(header_line(title, c, i == 0))
        if items == "STATS":
            right += stats_lines(stats, c)
            continue
        for it in items:
            right.append("" if it is None else kv_line(it[0], it[1].format(uptime=up), c))

    art = ascii_portrait(theme == "dark")
    rows = max(len(art), len(right))
    art_off = (rows - len(art)) // 2
    right_off = max(0, (rows - len(right)) // 2)
    left_w = (ASCII_WIDTH + 3) * CHAR_W
    W = int(PAD * 2 + left_w + COLS * CHAR_W + 12)
    H = int(PAD * 2 + rows * LINE_H)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Consolas,\'DejaVu Sans Mono\',Menlo,\'Courier New\',monospace" font-size="{FONT}px">',
           '<style>text{white-space:pre}</style>',
           f'<rect width="{W}" height="{H}" rx="15" fill="{c["bg"]}" stroke="{c["border"]}"/>']
    out.append(f'<text x="{PAD}" y="{PAD + LINE_H - 5}" fill="{c["text"]}" xml:space="preserve">')
    for i, line in enumerate(art):
        out.append(f'<tspan x="{PAD}" y="{PAD + (i + art_off + 1) * LINE_H - 5}">{escape(line)}</tspan>')
    out.append("</text>")
    x = PAD + left_w
    out.append(f'<text x="{x}" y="{PAD}" fill="{c["text"]}" xml:space="preserve">')
    for i, line in enumerate(right):
        out.append(f'<tspan x="{x}" y="{PAD + (i + right_off + 1) * LINE_H - 5}">{line}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    try:
        stats = gh_stats()
    except Exception as e:  # si la API falla, no rompe el SVG
        print("No se pudieron leer las stats:", e)
        stats = dict.fromkeys(["repos", "contrib", "stars", "commits", "followers", "loc", "add", "dele"], "?")
    up = uptime()
    for theme in THEMES:
        Path(f"{theme}_mode.svg").write_text(render(theme, stats, up), encoding="utf-8")
    print("OK →", up, stats)
