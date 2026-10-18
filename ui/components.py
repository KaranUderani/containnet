"""Small HTML building blocks (people strip, protect-first cards)."""
from __future__ import annotations

import html

from containnet.config import ROLE_NAMES


def people_strip(n: int, infected: float, protected: int = 0) -> str:
    """One square per person: red = infected on average, ink = protected, blue = spared."""
    inf = int(round(infected))
    cells = []
    for i in range(n):
        if i < inf:
            cells.append('<span class="cn-dot inf"></span>')
        elif i < inf + protected:
            cells.append('<span class="cn-dot prot"></span>')
        else:
            cells.append('<span class="cn-dot safe"></span>' if protected or inf < n else '<span class="cn-dot"></span>')
    return f'<div class="cn-strip">{"".join(cells)}</div>'


def strip_block(label_html: str, n: int, infected: float, protected: int = 0, baseline: bool = False) -> str:
    if baseline:
        inf = int(round(infected))
        cells = "".join('<span class="cn-dot inf"></span>' if i < inf else '<span class="cn-dot"></span>' for i in range(n))
        strip = f'<div class="cn-strip">{cells}</div>'
    else:
        strip = people_strip(n, infected, protected)
    return f'<div class="cn-strip-label">{label_html}</div>{strip}'


LEGEND = (
    '<div class="cn-legend">'
    '<span><i style="background:#D7263D"></i>infected (average)</span>'
    '<span><i style="background:#14262E"></i>protected</span>'
    '<span><i style="background:#B9DDE2"></i>spared</span>'
    '<span><i style="background:#C9D3D6"></i>not infected (no plan)</span>'
    "</div>"
)


def protect_card(rank: int, row, potential: float | None) -> str:
    role = ROLE_NAMES.get(row["role"], row["role"])
    chips = [f'<span class="cn-chip">Group {int(row["louvain_group"])}</span>']
    if int(row["cpm_groups"]) > 1:
        chips.append(f'<span class="cn-chip amber">In {int(row["cpm_groups"])} overlapping groups</span>')
    if potential is not None:
        chips.append(f'<span class="cn-chip red">Starts outbreaks of ~{potential:.0f}</span>')
    return (
        '<div class="cn-card">'
        f'<div class="cn-rank">{rank}</div>'
        "<div>"
        f'<div class="who">Person {html.escape(str(row["node"]))} <span class="cn-small">· {html.escape(role)}</span></div>'
        f'<div class="meta">{int(row["contacts"])} contacts · {int(row["strength"]):,} contact intervals</div>'
        f'{"".join(chips)}'
        "</div></div>"
    )
