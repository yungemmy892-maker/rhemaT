import json
from pathlib import Path

from django.core.management.base import BaseCommand

from bible.models import SUPPORTED_VERSIONS, Verse

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
FIXTURE_PATHS = {
    "KJV": DATA_DIR / "kjv_verses.json",
    "WEB": DATA_DIR / "web_verses.json",
}


class Command(BaseCommand):
    help = (
        "Loads the full KJV (King James Version) and/or WEB (World English "
        "Bible) text — both public domain — from data/*.json into MongoDB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            choices=["kjv", "web", "all"],
            default="all",
            help="Which version(s) to load. Defaults to both.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Drop existing documents for the selected version(s) before loading.",
        )

    def handle(self, *args, **options):
        versions = (
            list(SUPPORTED_VERSIONS)
            if options["version"] == "all"
            else [options["version"].upper()]
        )

        for version in versions:
            self._load_version(version, reset=options["reset"])

        self.stdout.write(
            self.style.SUCCESS(f"Done. {Verse.objects.count()} total verses in MongoDB.")
        )

    def _load_version(self, version: str, reset: bool):
        path = FIXTURE_PATHS[version]
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found for {version}: {path}"))
            return

        if reset:
            self.stdout.write(f"Dropping existing {version} verses...")
            Verse.objects(version=version).delete()

        existing = Verse.objects(version=version).count()
        if existing > 0 and not reset:
            self.stdout.write(
                self.style.WARNING(
                    f"{version} already has {existing} documents loaded. "
                    "Use --reset to reload from scratch. Skipping."
                )
            )
            return

        with open(path, encoding="utf-8") as f:
            records = json.load(f)

        self.stdout.write(f"Loading {len(records)} {version} verses...")

        docs = [
            Verse(
                book=r["book"],
                book_display=r["book_display"],
                testament=r["testament"],
                book_index=r["book_index"],
                chapter=r["chapter"],
                verse=r["verse"],
                text=r["text"],
                ref=r["ref"],
                text_lower=r["text"].lower(),
                version=version,
            )
            for r in records
        ]

        batch_size = 2000
        for i in range(0, len(docs), batch_size):
            Verse.objects.insert(docs[i : i + batch_size], load_bulk=False)
            self.stdout.write(f"  [{version}] inserted {min(i + batch_size, len(docs))}/{len(docs)}")

        self.stdout.write(self.style.SUCCESS(f"{version}: {Verse.objects(version=version).count()} verses loaded."))
