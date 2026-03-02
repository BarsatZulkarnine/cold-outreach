import asyncio
import re
import googlemaps
from config import GOOGLE_MAPS_API_KEY, DEFAULT_MAPS_QUERIES

# Keywords that indicate non-tech industries to filter out
EXCLUDE_KEYWORDS = [
    "mining", "oil", "gas", "petroleum", "coal", "excavat",
    "plumb", "electric", "construct", "real estate", "dental",
    "medical", "clinic", "restaurant", "café", "cafe", "hotel",
    "salon", "beauty", "childcare", "kindergarten",
]

# Coordinates for Melbourne tech suburbs — used to bias search results
# toward the actual suburb rather than CBD
SUBURB_COORDS: dict[str, tuple[float, float]] = {
    "cremorne":       (-37.8285, 144.9860),
    "richmond":       (-37.8219, 144.9997),
    "collingwood":    (-37.8025, 144.9885),
    "fitzroy":        (-37.7995, 144.9780),
    "south melbourne":(-37.8318, 144.9596),
    "hawthorn":       (-37.8225, 145.0326),
    "abbotsford":     (-37.8041, 144.9984),
    "prahran":        (-37.8501, 144.9919),
    "south yarra":    (-37.8401, 144.9919),
    "carlton":        (-37.7977, 144.9669),
    "docklands":      (-37.8148, 144.9456),
    "southbank":      (-37.8236, 144.9600),
    "st kilda":       (-37.8596, 144.9831),
    "northcote":      (-37.7703, 145.0073),
    "brunswick":      (-37.7700, 144.9619),
    "footscray":      (-37.8002, 144.8993),
    "box hill":       (-37.8197, 145.1228),
    "caulfield":      (-37.8779, 145.0420),
}

# Fallback: Melbourne geographic center (slightly south of CBD)
_MELBOURNE_CENTER = (-37.8136, 144.9631)
_MELBOURNE_RADIUS = 30000   # 30km covers all inner/mid suburbs
_SUBURB_RADIUS    = 4000    # tight 4km bias for suburb-specific queries


def _location_for_query(query: str) -> tuple[tuple[float, float], int]:
    """
    Returns (lat_lng, radius_meters) appropriate for the query.
    Suburb-specific queries get a tight radius around the suburb's center.
    Generic Melbourne queries use CBD with a broad radius.
    """
    q = query.lower()
    for suburb, coords in SUBURB_COORDS.items():
        if suburb in q:
            return coords, _SUBURB_RADIUS
    return _MELBOURNE_CENTER, _MELBOURNE_RADIUS


def _is_likely_tech(place: dict) -> bool:
    name = (place.get("name") or "").lower()
    types = place.get("types") or []

    for kw in EXCLUDE_KEYWORDS:
        if kw in name:
            return False

    # Google Places types that are clearly not tech
    non_tech_types = {
        "restaurant", "food", "bar", "lodging", "beauty_salon",
        "dentist", "doctor", "hospital", "school", "church",
        "grocery_or_supermarket", "gas_station",
    }
    if any(t in non_tech_types for t in types):
        return False

    # Must have at least 3 ratings to be credible
    if place.get("user_ratings_total", 0) < 3:
        return False

    return True


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1).lower() if match else None


async def scrape_google_maps(
    queries: list[str] | None = None,
    max_results_per_query: int = 20,
) -> list[dict]:
    """
    Search Google Maps for tech companies in Melbourne.
    Each query is biased toward its suburb's GPS coordinates (not always CBD).
    Paginates through up to 3 pages (60 results) per query before filtering.
    Returns a list of company dicts — does NOT persist to DB.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not set in .env")

    if queries is None:
        queries = DEFAULT_MAPS_QUERIES

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    seen_domains: set[str] = set()
    results: list[dict] = []

    for query in queries:
        location, radius = _location_for_query(query)
        print(f"[Maps] Searching: {query!r}  (bias {location}, r={radius}m)")

        # ── First page ────────────────────────────────────────────────────────
        try:
            response = gmaps.places(
                query=query,
                location=location,
                radius=radius,
                language="en",
            )
        except Exception as e:
            print(f"[Maps] Error for query {query!r}: {e}")
            await asyncio.sleep(1)
            continue

        all_places: list[dict] = list(response.get("results", []))
        next_page_token: str | None = response.get("next_page_token")

        # ── Paginate (up to 2 more pages = 60 total) ──────────────────────────
        while next_page_token:
            # Google requires ~2s before the token becomes valid
            await asyncio.sleep(2)
            try:
                paged = gmaps.places(page_token=next_page_token)
                all_places.extend(paged.get("results", []))
                next_page_token = paged.get("next_page_token")
            except Exception as e:
                print(f"[Maps] Pagination error: {e}")
                break

        print(f"[Maps]   {len(all_places)} raw places fetched for this query")

        # ── Process places ────────────────────────────────────────────────────
        count = 0
        for place in all_places:
            if count >= max_results_per_query:
                break

            if not _is_likely_tech(place):
                continue

            place_id = place.get("place_id")
            if not place_id:
                continue

            # Get detailed info
            try:
                detail_resp = gmaps.place(
                    place_id=place_id,
                    fields=["name", "website", "formatted_address",
                            "formatted_phone_number", "rating", "user_ratings_total"],
                )
                detail = detail_resp.get("result", {})
            except Exception as e:
                print(f"[Maps] Detail fetch error for {place.get('name')}: {e}")
                await asyncio.sleep(0.5)
                continue

            website = detail.get("website")
            domain = _extract_domain(website)

            # Deduplicate by domain across all queries in this run
            if domain and domain in seen_domains:
                await asyncio.sleep(0.2)
                continue
            if domain:
                seen_domains.add(domain)

            company = {
                "source": "google_maps",
                "company_name": detail.get("name") or place.get("name"),
                "company_website": website,
                "company_size": None,
                "tech_stack": [],
                "contact_name": None,
                "contact_title": None,
                "contact_email": None,
                "linkedin_url": None,
                "has_open_roles": False,
                "open_role_url": None,
                "notes": (
                    f"Address: {detail.get('formatted_address', 'N/A')} | "
                    f"Phone: {detail.get('formatted_phone_number', 'N/A')} | "
                    f"Rating: {detail.get('rating', 'N/A')} "
                    f"({detail.get('user_ratings_total', 0)} reviews)"
                ),
                "status": "discovered",
            }

            results.append(company)
            count += 1
            print(f"[Maps]   ✓ {company['company_name']} — {website or 'no website'}")

            await asyncio.sleep(0.5)  # rate limit between detail calls

        # Pause between queries
        await asyncio.sleep(1)
        print(f"[Maps] Query done. Got {count} results. Total so far: {len(results)}")

    print(f"[Maps] Done. Total companies found: {len(results)}")
    return results
