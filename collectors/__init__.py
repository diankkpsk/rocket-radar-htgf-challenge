"""Public source collection entry point."""

from . import htgf, kit, tum
from .reviewed import apply
from .fetch import CollectionError, Fetcher

ADAPTERS = {"htgf": htgf.collect, "kit": kit.collect, "tum": tum.collect}


def collect(source_id):
    if source_id not in ADAPTERS:
        raise CollectionError("Unrecognized directory source")
    return apply(ADAPTERS[source_id](Fetcher(max_requests=22)))
