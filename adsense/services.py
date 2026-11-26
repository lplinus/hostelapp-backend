import random
from django.utils import timezone
from django.db.models import F, Q
from django.core.cache import cache
from .models import AdCampaign


def get_active_banner_campaigns(
    property_type,
    city=None,
    city_slug=None,
    city_id=None,
    placement=None,
    limit=4,
    search_id=None,
):
    """
    Selects and caches active banner campaigns for the given property type and location.
    - search_id: Search context / session token generated on each page load/reload.
      When present, caches for 30s per search_id so concurrent requests on that load
      (the banner API + the catalog card list API) share the exact same selection.
      When omitted, uses a fast rolling 10-second cache window.
    - Limit is maximum 4 items for the billboard banner
    - Fixed schedule: start_date <= now <= end_date
    - Budget cap: max_impressions / max_clicks
    - Weighted random: picks properties by weight per search session
    Returns a list of AdCampaign model instances.
    """
    prop_type = (property_type or "all").lower().strip()
    city_str = (city or city_slug or str(city_id or "all")).lower().replace(" ", "_").strip()
    placement_str = (placement or "all").lower().strip()

    if search_id and str(search_id).strip():
        s_id = str(search_id).strip()
        cache_key = f"active_banner_{prop_type}_{city_str}_{placement_str}_{s_id}"
        cache_ttl = 30
    else:
        cache_key = f"active_banner_{prop_type}_{city_str}_{placement_str}_rolling"
        cache_ttl = 10

    cached_campaign_ids = cache.get(cache_key)
    if cached_campaign_ids is not None:
        campaigns = list(
            AdCampaign.objects.filter(
                id__in=cached_campaign_ids,
                is_deleted=0,
                status=AdCampaign.CampaignStatus.ACTIVE,
            ).select_related("hotel", "vacation_rental", "hotel__city", "vacation_rental__city", "hostel")
        )
        if campaigns:
            # Preserve cached order
            order_map = {cid: idx for idx, cid in enumerate(cached_campaign_ids)}
            campaigns.sort(key=lambda c: order_map.get(c.id, 999))
            effective_limit = min(limit or 4, 4)
            return campaigns[:effective_limit]

    now = timezone.now()
    queryset = AdCampaign.objects.filter(
        is_deleted=0,
        status=AdCampaign.CampaignStatus.ACTIVE,
        start_date__lte=now,
        end_date__gte=now,
    ).select_related("hotel", "vacation_rental", "hotel__city", "vacation_rental__city", "hostel")

    # Budget stop
    queryset = queryset.exclude(
        Q(max_impressions__gt=0, impressions_count__gte=F("max_impressions"))
        | Q(max_clicks__gt=0, clicks_count__gte=F("max_clicks"))
    )

    if prop_type != "all":
        queryset = queryset.filter(property_type=prop_type)

    if placement and placement != "all":
        queryset = queryset.filter(placement=placement)

    if city_id:
        queryset = queryset.filter(Q(hotel__city_id=city_id) | Q(vacation_rental__city_id=city_id))
    elif city_slug:
        queryset = queryset.filter(Q(hotel__city__slug=city_slug) | Q(vacation_rental__city__slug=city_slug))
    elif city and city.strip():
        c = city.strip()
        queryset = queryset.filter(
            Q(hotel__city__name__icontains=c)
            | Q(vacation_rental__city__name__icontains=c)
            | Q(hotel__address__icontains=c)
            | Q(vacation_rental__address__icontains=c)
            | Q(hotel__area__name__icontains=c)
            | Q(vacation_rental__area__name__icontains=c)
        )

    all_campaigns = list(queryset)
    if not all_campaigns:
        cache.set(cache_key, [], timeout=cache_ttl)
        return []

    # Weighted random selection (maximum of 4 unique property banner slots)
    max_slots = 4
    selected = []
    seen_property_ids = set()
    pool = list(all_campaigns)
    while pool and len(selected) < max_slots:
        weights = [max(1, getattr(item, "weight", 1) or 1) for item in pool]
        choice = random.choices(pool, weights=weights, k=1)[0]
        pool.remove(choice)
        prop_id = choice.hotel_id or choice.vacation_rental_id or choice.hostel_id
        if prop_id and prop_id in seen_property_ids:
            continue
        if prop_id:
            seen_property_ids.add(prop_id)
        selected.append(choice)

    cache.set(cache_key, [c.id for c in selected], timeout=cache_ttl)
    effective_limit = min(limit or 4, 4)
    return selected[:effective_limit]


def get_active_banner_property_ids(
    property_type,
    city=None,
    city_slug=None,
    city_id=None,
    limit=4,
    search_id=None,
):
    """
    Returns the set of property IDs (UUIDs or strings) currently being served
    in the active banner (max 4) for the given property type, location, and search session.
    Used by Hotel and VacationRental ViewSets to mutually exclude banner properties
    from the public search and catalog feeds in the backend.
    """
    p_type = (property_type or "").lower().strip()
    campaigns = get_active_banner_campaigns(
        property_type=p_type,
        city=city,
        city_slug=city_slug,
        city_id=city_id,
        limit=min(limit or 4, 4),
        search_id=search_id,
    )
    property_ids = set()
    for c in campaigns:
        if p_type == "hotel" and c.hotel_id:
            property_ids.add(c.hotel_id)
        elif p_type in ["vacation_rental", "vacationrental", "vacation-rental"] and c.vacation_rental_id:
            property_ids.add(c.vacation_rental_id)
        elif c.hostel_id and p_type == "hostel":
            property_ids.add(c.hostel_id)
    return property_ids
