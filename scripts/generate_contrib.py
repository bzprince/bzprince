"""Generate assets/city.svg (isometric "Contribution City") from a user's public GitHub contributions.
No token needed. Run by GitHub Actions every few hours."""
import datetime
import os
import re
import urllib.request

USER = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "bzprince"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "city.svg")


def fetch():
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (contribution-city)"},
    )
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def parse(html):
    cells = re.findall(
        r'<td[^>]*data-date="([0-9-]+)"[^>]*id="contribution-day-component-(\d+)-(\d+)"[^>]*data-level="(\d)"', html)
    tips = dict(re.findall(r'for="contribution-day-component-(\d+-\d+)"[^>]*>([^<]*)<', html))
    grid = {}
    for date, r, c, lvl in cells:
        m = re.match(r"(\d+) contribution", tips.get(f"{r}-{c}", ""))
        grid[(int(r), int(c))] = (date, int(lvl), int(m.group(1)) if m else 0)
    if not grid:
        raise SystemExit("could not parse contributions")
    return grid


def build(grid):
    cols = max(c for _, c in grid) + 1
    total = sum(v[2] for v in grid.values())
    active = sum(1 for v in grid.values() if v[2] > 0)
    peak = max(v[2] for v in grid.values())
    last_date = max(v[0] for v in grid.values())
    today = datetime.date.fromisoformat(last_date).strftime("%b %d, %Y").replace(" 0", " ")

    W, H = 820, 340
    w, h = 7.0, 3.5          # iso half tile width / height
    X0 = 372 + 6 * w - 6 * w  # x of column 0,row 0
    Y0 = 84
    maxh = 92
    F = "font-family:'Fira Code','JetBrains Mono',Consolas,monospace;"

    pal = {  # level: (top, left, right)
        0: ("#143a25", "#0d2a1a", "#0a2115"),
        1: ("#2e7d32", "#1f5a24", "#184a1d"),
        2: ("#3f9a3a", "#2c7a2c", "#236523"),
        3: ("#4da33e", "#3a8a30", "#2d7226"),
        4: ("#a6f09a", "#6fcf62", "#4da33e"),
    }

    def box(c, r, hgt, lvl):
        sx = X0 + (c - r) * w
        sy = Y0 + (c + r) * h
        t, l, rr = pal[lvl]
        top = f"{sx:.1f},{sy-hgt:.1f} {sx+w:.1f},{sy-hgt+h:.1f} {sx:.1f},{sy-hgt+2*h:.1f} {sx-w:.1f},{sy-hgt+h:.1f}"
        left = f"{sx-w:.1f},{sy-hgt+h:.1f} {sx:.1f},{sy-hgt+2*h:.1f} {sx:.1f},{sy+2*h:.1f} {sx-w:.1f},{sy+h:.1f}"
        right = f"{sx+w:.1f},{sy-hgt+h:.1f} {sx:.1f},{sy-hgt+2*h:.1f} {sx:.1f},{sy+2*h:.1f} {sx+w:.1f},{sy+h:.1f}"
        return (f'<polygon points="{left}" fill="{l}"/><polygon points="{right}" fill="{rr}"/>'
                f'<polygon points="{top}" fill="{t}"/>'), sx, sy - hgt

    o = []
    o.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
text{{{F}}}
.col{{opacity:0;animation:rise .7s ease forwards}}
@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
.tw{{animation:pulse 2.4s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:.9}}50%{{opacity:.35}}}}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0c2a19"/><stop offset=".55" stop-color="#08170f"/><stop offset="1" stop-color="#06100a"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4da33e"/><stop offset=".5" stop-color="#104d2b"/><stop offset="1" stop-color="#4da33e"/></linearGradient>
<radialGradient id="gl" cx="82%" cy="78%" r="55%"><stop offset="0" stop-color="#4da33e" stop-opacity=".30"/><stop offset="1" stop-color="#4da33e" stop-opacity="0"/></radialGradient>
<filter id="blur" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
<clipPath id="cp"><rect x="2" y="2" width="{W-4}" height="{H-4}" rx="20"/></clipPath>
</defs>
<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#cp)"><rect width="{W}" height="{H}" fill="url(#gl)"/></g>
<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="20" fill="none" stroke="url(#bd)" stroke-width="1.6"/>
<text x="40" y="62" font-size="12" font-weight="700" letter-spacing="3" fill="#4da33e">CONTRIBUTION CITY</text>
<text x="40" y="118" font-size="56" font-weight="700" fill="#e9fbe6">{total}</text>
<text x="40" y="146" font-size="14" fill="#9be58d">contributions in the last year</text>
<text x="40" y="186" font-size="14" font-weight="700" fill="#b6f5a8">{active} active day{"s" if active != 1 else ""}</text>
<text x="40" y="208" font-size="14" font-weight="700" fill="#b6f5a8">Busiest day: {peak}</text>
<text x="40" y="288" font-size="13" fill="#4da33e">@{USER}</text>
<text x="40" y="308" font-size="11" fill="#5b7a62">updated {today} · auto-refresh</text>
''')
    tower = None
    # draw by column (back to front); inside a column by r ascending (depth = c + r)
    for c in range(cols):
        o.append(f'<g class="col" style="animation-delay:{c*0.03:.2f}s">')
        for r in range(7):
            if (r, c) not in grid:
                continue
            d, lvl, n = grid[(r, c)]
            hgt = 2.0 if n == 0 else 6 + (n / peak) ** 0.55 * (maxh - 6)
            use_lvl = 0 if n == 0 else max(lvl, 1)
            svg, sx, ty = box(c, r, hgt, use_lvl)
            o.append(svg)
            if n == peak and n > 0:
                tower = (sx, ty)
        o.append("</g>")
    if tower:
        sx, ty = tower
        o.append(f'<ellipse class="tw" cx="{sx:.1f}" cy="{ty+h:.1f}" rx="{w*1.8:.1f}" ry="{h*2.2:.1f}" fill="#a6f09a" filter="url(#blur)"/>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    svg = build(parse(fetch()))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT)
