import asyncio
import re
from datetime import datetime
import googlemaps
from config import GOOGLE_MAPS_API_KEY, DEFAULT_MAPS_QUERIES

# Keywords that indicate non-tech industries to filter out
EXCLUDE_KEYWORDS = [
    "mining", "oil", "gas", "petroleum", "coal", "excavat",
    "plumb", "electric", "construct", "real estate", "dental",
    "medical", "clinic", "restaurant", "café", "cafe", "hotel",
    "salon", "beauty", "childcare", "kindergarten",
]


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
        print(f"[Maps] Searching: {query!r}")
        try:
            response = gmaps.places(
                query=query,
                location=(-37.8136, 144.9631),  # Melbourne CBD
                radius=30000,                    # 30km radius
                language="en",
            )
        except Exception as e:
            print(f"[Maps] Error for query {query!r}: {e}")
            await asyncio.sleep(1)
            continue

        places = response.get("results", [])
        count = 0

        for place in places:
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

            # Deduplicate by domain
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
