"""TUM competition listings, with reviewed annotations guarded by source text."""

import re

from .common import evidence, excerpt, record, slug, utc_now
from .dom import Tree
from .fetch import CollectionError

URL = "https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward"
PUBLISHER = "Technical University of Munich"

# Summaries and sector labels are editorial interpretations. A literal anchor
# guards against applying them to a different project with the same name.
ANNOTATIONS = {
    "IsoSphere Technologies": (
        "¹³C-labelled molecules",
        "Life Sciences",
        "Develops a European supply of carbon-13-labelled compounds for research and diagnostics.",
    ),
    "SOward": (
        "SO4ward is developing their invention CatLyst",
        "Water Technology",
        "The SO4ward team is developing CatLyst to treat PFAS-contaminated water.",
    ),
    "RNAvia": (
        "RiboTAB",
        "Therapeutics",
        "Develops an oral RNA medicine for inflammatory bowel disease.",
    ),
    "IARET Catalysis": (
        "recovering precious metals",
        "Circular Economy",
        "Develops a recycling process to recover precious metals from spent vehicle catalysts.",
    ),
    "AccessMRI": (
        "point-of-care musculoskeletal imaging",
        "Medtech",
        "Develops compact MRI equipment for orthopaedic practices and other points of care.",
    ),
    "Cellium Biotech": (
        "lab-scale bioreactors",
        "Industrial Biotech",
        "Develops research equipment and software for monitoring fermentation.",
    ),
    "PhAI Bio": (
        "advanced preclinical testing",
        "Therapeutics",
        "Develops antifibrotic medicines. The finalist profile describes preclinical work on lung and skin disease.",
    ),
    "ChondroVene": (
        "joint injuries and early osteoarthritis",
        "Therapeutics",
        "Develops a cartilage repair therapy for joint injuries and early osteoarthritis.",
    ),
    "Sona8": (
        "AI voice agents",
        "Enterprise Software",
        "Builds voice software that interviews employees about their work to identify process improvements.",
    ),
    "EcoWeave": (
        "early-stage startup concept",
        "Advanced Materials",
        "Designs a coating for textile yarn to reduce the release of microplastic fibres.",
    ),
}

DEMAND = "more than 60 customer interviews and 14 Letters of Intent"
YC = "Sona8 has already conducted more than 10,000 interviews and is backed by Y Combinator."


def parse(markup, observed):
    nodes = list(Tree(markup).root.walk())
    result = []
    year = None
    for node in nodes:
        # Only read panels in the finalists section, never programme FAQs or archives.
        if node.tag == "h2":
            heading = re.search(
                r"finalists of the TUM IDEAward (20\d{2})", node.text(), re.I
            )
            year = heading.group(1) if heading else None
        if not year or not node.has_class("in2template-accordion"):
            continue
        name = node.first_text("in2template-accordion__title")
        body = node.first_text("in2template-accordion__panel")
        if not name or not body:
            raise CollectionError("A TUM finalist panel has no title or description")
        r = record("tum-" + slug(name), name)
        title = "TUM IDEAward " + year + " finalists"
        url = URL
        anchor = node.attrs.get("id", "")
        if re.fullmatch(r"c\d+", anchor):
            url += "#" + anchor
        r.update(
            university="Technical University of Munich",
            tags=["TUM IDEAward", "Finalist"],
        )
        annotation = ANNOTATIONS.get(name)
        if annotation and annotation[0] in body:
            quote, r["sector"], r["summary"] = annotation
        else:
            quote = excerpt(body, 17)
            r["summary"] = (
                "Selected as a TUM IDEAward finalist. The project is described in the source."
            )
        r["evidence"].append(
            evidence(
                "tum",
                PUBLISHER,
                url,
                title,
                quote,
                name + " appears in the " + year + " TUM IDEAward finalist cohort.",
                "COMPETITION_FINALIST",
                observed,
            )
        )
        if name == "IsoSphere Technologies" and DEMAND in body:
            r["evidence"].append(
                evidence(
                    "tum",
                    PUBLISHER,
                    url,
                    title,
                    DEMAND,
                    "The team's TUM profile reports over 60 customer interviews and 14 letters of intent.",
                    "CUSTOMER_DISCOVERY",
                    observed,
                )
            )
        if name == "Sona8" and YC in body:
            r.update(stage="EXISTING_EMERGING", funding_status="REPORTED_BACKING")
            r["evidence"].append(
                evidence(
                    "tum",
                    PUBLISHER,
                    url,
                    title,
                    YC,
                    "The finalist profile reports Y Combinator backing and more than 10,000 interviews.",
                    "REPORTED_BACKING",
                    observed,
                )
            )
        if (
            name == "AccessMRI"
            and "now being integrated into a functional prototype" in body
        ):
            r["evidence"].append(
                evidence(
                    "tum",
                    PUBLISHER,
                    url,
                    title,
                    "now being integrated into a functional prototype",
                    "The team reports integration work on its imaging prototype.",
                    "PROTOTYPE",
                    observed,
                )
            )
        result.append(r)
    if not result or len({r["id"] for r in result}) != len(result):
        raise CollectionError(
            "Could not identify a unique TUM IDEAward finalist cohort"
        )
    return result


def collect(fetcher):
    markup = fetcher.get(URL)
    return parse(markup, utc_now())
