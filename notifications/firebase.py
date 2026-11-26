import logging
import os
from typing import List, Dict, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False

def get_firebase_app():
    """
    Safely initializes and returns the default Firebase Admin App singleton.
    """
    global _firebase_initialized
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cert_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', None)
            if not cert_path:
                cert_path = os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')
            elif not os.path.isabs(cert_path):
                cert_path = os.path.join(settings.BASE_DIR, cert_path)

            if os.path.exists(cert_path):
                cred = credentials.Certificate(cert_path)
                app = firebase_admin.initialize_app(cred)
                _firebase_initialized = True
                logger.info(f"Firebase Admin SDK initialized successfully with certificate: {cert_path}")
                return app
            else:
                logger.warning(f"Firebase certificate not found at {cert_path}. Push notifications will be disabled.")
                return None
        return firebase_admin.get_app()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        return None


def send_fcm_multicast(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    click_action: Optional[str] = None
) -> Dict[str, int]:
    """
    Sends a push notification to multiple FCM registration tokens.
    Automatically deactivates unregistered or stale tokens from the database.
    """
    if not tokens:
        return {"success_count": 0, "failure_count": 0}

    app = get_firebase_app()
    if not app:
        logger.warning("Firebase app is not initialized. Skipping push notification.")
        return {"success_count": 0, "failure_count": len(tokens)}

    try:
        from firebase_admin import messaging
        from .models import FCMDevice

        # Format string values for the data payload
        formatted_data = {}
        if data:
            for k, v in data.items():
                if v is not None:
                    formatted_data[str(k)] = str(v)

        webpush_config = None
        if click_action:
            webpush_config = messaging.WebpushConfig(
                fcm_options=messaging.WebpushFCMOptions(link=click_action)
            )

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=formatted_data,
            tokens=tokens,
            webpush=webpush_config,
        )

        response = messaging.send_each_for_multicast(message)

        # Detect stale or unregistered tokens and mark them inactive
        stale_tokens = []
        for idx, resp in enumerate(response.responses):
            if not resp.success and resp.exception:
                err_code = getattr(resp.exception, 'code', None)
                if isinstance(resp.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)) or err_code == 'registration-token-not-registered':
                    stale_tokens.append(tokens[idx])

        if stale_tokens:
            updated = FCMDevice.objects.filter(registration_token__in=stale_tokens).update(is_active=False)
            logger.info(f"Deactivated {updated} stale FCM registration tokens.")

        logger.info(f"FCM push complete: {response.success_count} succeeded, {response.failure_count} failed.")
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count
        }
    except Exception as e:
        logger.error(f"Error executing FCM multicast send: {e}", exc_info=True)
        return {"success_count": 0, "failure_count": len(tokens)}
