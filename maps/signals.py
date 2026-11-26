from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from .tasks import invalidate_maps_cache


def register_maps_signals():
    """
    Registers cache-invalidation signals for Hotels, Vacation Rentals,
    MapPlaces, and PropertyPinpoints so any added or updated property
    is immediately reflected on the live map without waiting.
    """
    try:
        Hotel = apps.get_model("hotels", "Hotel")
        post_save.connect(on_property_changed, sender=Hotel, dispatch_uid="maps_hotel_post_save")
        post_delete.connect(on_property_changed, sender=Hotel, dispatch_uid="maps_hotel_post_delete")
    except Exception as e:
        pass

    try:
        VacationRental = apps.get_model("vacanationrentals", "VacationRental")
        post_save.connect(on_property_changed, sender=VacationRental, dispatch_uid="maps_vr_post_save")
        post_delete.connect(on_property_changed, sender=VacationRental, dispatch_uid="maps_vr_post_delete")
    except Exception as e:
        pass

    try:
        PropertyPinpoint = apps.get_model("maps", "PropertyPinpoint")
        post_save.connect(on_property_changed, sender=PropertyPinpoint, dispatch_uid="maps_pinpoint_post_save")
        post_delete.connect(on_property_changed, sender=PropertyPinpoint, dispatch_uid="maps_pinpoint_post_delete")
    except Exception as e:
        pass

    try:
        MapPlace = apps.get_model("maps", "MapPlace")
        post_save.connect(on_property_changed, sender=MapPlace, dispatch_uid="maps_place_post_save")
        post_delete.connect(on_property_changed, sender=MapPlace, dispatch_uid="maps_place_post_delete")
    except Exception as e:
        pass


def on_property_changed(sender, instance, **kwargs):
    """
    Wipes the cached GeoJSON collection instantly.
    """
    invalidate_maps_cache()
