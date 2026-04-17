"""
Management Command: generate_hostel_ai

Batch-processes hostels that need AI description generation.
Targets hostels where ai_hash is NULL (invalidated or never generated).

Usage:
    python manage.py generate_hostel_ai              # Process all stale hostels
    python manage.py generate_hostel_ai --limit 10   # Process at most 10
    python manage.py generate_hostel_ai --force       # Regenerate ALL hostels
    python manage.py generate_hostel_ai --dry-run     # Preview without calling AI
"""

import time
import logging
from django.core.management.base import BaseCommand
from hostels.models import Hostel
from AI.hostel_ai_service import HostelAIService

logger = logging.getLogger("ai.service")


class Command(BaseCommand):
    help = "Generate AI descriptions for hostels with stale or missing AI content."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of hostels to process. 0 = unlimited.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Force regeneration for ALL hostels, ignoring cache.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview which hostels would be processed without calling AI.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.5,
            help="Delay in seconds between API calls to avoid rate limiting.",
        )

    def handle(self, *args, **options) -> None:
        limit: int = options["limit"]
        force: bool = options["force"]
        dry_run: bool = options["dry_run"]
        delay: float = options["delay"]

        # ── Build queryset ────────────────────────────────────────────────
        qs = (
            Hostel.objects
            .filter(is_active=True)
            .select_related("city", "area")
            .prefetch_related("amenities")
        )

        if not force:
            # Only process hostels with stale/missing AI content
            qs = qs.filter(ai_hash__isnull=True)

        if limit > 0:
            qs = qs[:limit]

        hostels = list(qs)
        total = len(hostels)

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("[OK] All hostels have up-to-date AI descriptions.")
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}"
                f"Found {total} hostel(s) to process..."
            )
        )

        # ── Process each hostel ───────────────────────────────────────────
        success_count = 0
        error_count = 0

        for idx, hostel in enumerate(hostels, start=1):
            self.stdout.write(
                f"  [{idx}/{total}] {hostel.name} "
                f"(ID={hostel.pk}, city={hostel.city.name if hostel.city else 'N/A'})"
            )

            if dry_run:
                self.stdout.write(self.style.NOTICE("    -> Would generate (dry run)"))
                success_count += 1
                continue

            try:
                if force:
                    # Clear hash to force regeneration
                    hostel.ai_hash = None

                description = HostelAIService.generate_description(hostel)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"    -> Generated ({len(description)} chars)"
                    )
                )
                success_count += 1

                # Rate limit between API calls
                if idx < total:
                    time.sleep(delay)

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"    -> FAILED: {e}")
                )
                logger.error(f"generate_hostel_ai failed for '{hostel.name}': {e}")

        # ── Summary ───────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}"
                f"Done! {success_count} succeeded, {error_count} failed "
                f"(out of {total} total)"
            )
        )
