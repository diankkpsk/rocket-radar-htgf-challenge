"""Discover and verify KIT FORGE founder interview pages."""

from datetime import datetime
import re
from urllib.parse import urljoin, urlsplit

from .common import evidence, excerpt, public_link, record, slug, utc_now
from .dom import Tree
from .fetch import CollectionError

HOST = "www.kit-forge.de"
URL = "https://" + HOST + "/en/magazine/"
TITLE_PREFIX = "Founder of the month:"

# The portfolio has no authority over the legal registration of a project.
# Use article-specific anchors for reviewed tags, founder identity and self-reports.
ANNOTATIONS = {
    "OnSite Solutions": (
        "BAIOSS",
        "Property Technology",
        "Develops BAIOSS, a platform that assesses a building's digital systems and identifies improvements.",
    ),
    "mableAI": (
        "advertising algorithms",
        "Marketing Technology",
        "Helps online retailers use their store data to improve advertising performance and profitability.",
    ),
    "Charge Circle": (
        "charging points at logistics depots",
        "Mobility",
        "Connects electric lorry fleets with private charging capacity at logistics depots.",
    ),
    "data revolution": (
        "EU Data Act",
        "Enterprise Software",
        "Develops software to help companies access and use data from connected devices.",
    ),
    "marton.ai": (
        "real estate photos",
        "Property Technology",
        "Turns property photographs into videos for real estate agents and developers.",
    ),
    "RAZO Energy": (
        "heat pumps, and battery storage systems",
        "Energy",
        "Develops software to adjust electricity use by vehicles, heat pumps and batteries to renewable power availability.",
    ),
}

# Each anchor appears as a contiguous passage on the named profile.
PEOPLE = {
    "OnSite Solutions": (
        "was founded by Dr. Tristan Emich, Dr. Tobias Kropp, and Mario Dropulić",
        ["Tristan Emich", "Tobias Kropp", "Mario Dropulić"],
    ),
    "mableAI": ("Mable was founded by Nils Jessen", ["Nils Jessen"]),
    "Charge Circle": (
        "Joshua Enahoro and Sinah-Nikola Enahoro are asking with their start-up",
        ["Joshua Enahoro", "Sinah-Nikola Enahoro"],
    ),
    "data revolution": (
        "founded by Philip Schütz, Dennis Häring, Johannes Birkenmaier and Sarin Ravishanker",
        ["Philip Schütz", "Dennis Häring", "Johannes Birkenmaier", "Sarin Ravishanker"],
    ),
    "marton.ai": (
        "founded by Antonia Dieterich, Mario Quint, and Marcel Doll",
        ["Antonia Dieterich", "Mario Quint", "Marcel Doll"],
    ),
}
FINANCE = {
    "OnSite Solutions": (
        "receiving funding through the EXIST Startup Grant",
        "REPORTED_GRANT",
        "EXIST_GRANT",
    ),
    "Charge Circle": (
        "receiving funding through the exist program",
        "REPORTED_GRANT",
        "EXIST_GRANT",
    ),
    "RAZO Energy": (
        "thanks to EXIST start-up funding",
        "REPORTED_GRANT",
        "EXIST_GRANT",
    ),
    "mableAI": (
        "investors who later supported our pre-seed funding",
        "REPORTED_EQUITY",
        "REPORTED_BACKING",
    ),
    "marton.ai": (
        "we were able to secure the “Start-up BW Pre-Seed” grant",
        "REPORTED_GRANT",
        "STARTUP_GRANT",
    ),
    "data revolution": (
        "At the moment, everything is still completely bootstrapped",
        "REPORTED_BOOTSTRAPPED",
        "FUNDING_STATUS",
    ),
}


def index(markup):
    items = []
    for a in Tree(markup).root.walk():
        if a.tag != "a" or not a.has_class("flowTeaser__item"):
            continue
        title = a.first_text("h3")
        if (
            not title.startswith(TITLE_PREFIX)
            or a.first_text("flowTeaser__category") != "Founder of the month"
        ):
            continue
        link = urljoin(URL, a.attrs.get("href", ""))
        parts = urlsplit(link)
        if (
            parts.scheme != "https"
            or parts.netloc != HOST
            or parts.query
            or parts.fragment
            or not re.fullmatch(r"/en/magazine/[a-z0-9-]+/", parts.path)
        ):
            raise CollectionError("Unexpected KIT founder profile URL")
        if link not in items:
            items.append(link)
    if not items:
        raise CollectionError(
            "Could not identify any founder interviews in the KIT magazine"
        )
    return items


def parse(markup, url, observed):
    nodes = list(Tree(markup).root.walk())
    title = next((n.text() for n in nodes if n.tag == "h1"), "")
    if not title.startswith(TITLE_PREFIX):
        raise CollectionError("KIT profile has no founder interview heading")
    name = title.removeprefix(TITLE_PREFIX).strip()
    caption = next((n.text() for n in nodes if n.has_class("teaserImage__caption")), "")
    body = " ".join(n.text() for n in nodes if n.tag in {"p", "figcaption"})
    dates = [n.text() for n in nodes if n.has_class("articleIntro__date")]
    published = (
        datetime.strptime(dates[0], "%d.%m.%Y").date().isoformat() if dates else None
    )
    if not name or not caption:
        raise CollectionError("Incomplete KIT founder profile")
    r = record("kit-" + slug(name), name, stage="EXISTING_EMERGING")

    def add(quote, claim, signal):
        r["evidence"].append(
            evidence(
                "kit",
                "KIT FORGE",
                url,
                title,
                quote,
                claim,
                signal,
                observed,
                published,
            )
        )

    r.update(
        tags=["KIT FORGE", "Founder interview"],
        university="Karlsruhe Institute of Technology",
    )
    left = ANNOTATIONS.get(name)
    if left and left[0] in body:
        quote, r["sector"], r["summary"] = left
    else:
        quote = excerpt(caption, 16)
        r["summary"] = "Featured in a KIT FORGE founder interview."
    add(
        quote,
        "KIT FORGE published a founder interview about " + name + ".",
        "FOUNDER_INTERVIEW",
    )
    if "Karlsruhe-based startup" in caption:
        r.update(city="Karlsruhe", country="DE")
    names = PEOPLE.get(name)
    if names and names[0] in body:
        r["team"] = [
            {"name": person, "role": "Founder", "source_url": url}
            for person in names[1]
        ]
        add(names[0], "The interview identifies the founding team.", "TEAM_FORMATION")
    status = FINANCE.get(name)
    if status and status[0] in body:
        anchor, r["funding_status"], signal = status
        add(
            anchor,
            "Interview disclosures describe the team's financing at publication.",
            signal,
        )
    planning = "still due to formally incorporate in Q3 this year"
    if planning in body:
        r["stage"] = "POTENTIAL_PRE_COMPANY"
        add(
            planning,
            "The team described incorporation as a future step in its June 2026 interview. Current status needs checking.",
            "FOUNDING_INTENT",
        )
    # Only a direct publisher link labelled with the company name is a company site.
    labels = {slug(name)}
    if name == "mableAI":
        labels.add("mable")
    for a in nodes:
        if a.tag == "a" and slug(a.text()) in labels:
            href = public_link(a.attrs.get("href"))
            if href and urlsplit(href).hostname != HOST:
                r["website"] = href
                break
    return r


def collect(fetcher):
    links = index(fetcher.get(URL))
    if len(links) > 16:
        raise CollectionError("KIT founder list exceeded the 16-profile scan limit")
    rows = []
    for link in links:
        page = fetcher.get(link)
        rows.append(parse(page, link, utc_now()))
    return rows
