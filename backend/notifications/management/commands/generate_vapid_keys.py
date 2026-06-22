import base64

from django.core.management.base import BaseCommand
from py_vapid import Vapid


class Command(BaseCommand):
    help = "Generates a VAPID keypair for Web Push and prints it for your .env file."

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()

        private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        private_b64 = base64.urlsafe_b64encode(private_raw).rstrip(b"=").decode()

        public_numbers = vapid.public_key.public_numbers()
        x = public_numbers.x.to_bytes(32, "big")
        y = public_numbers.y.to_bytes(32, "big")
        public_raw = b"\x04" + x + y
        public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode()

        self.stdout.write(self.style.SUCCESS("Add these to your backend/.env:"))
        self.stdout.write(f"VAPID_PUBLIC_KEY={public_b64}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_b64}")
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Add this to your frontend/.env (must match VAPID_PUBLIC_KEY above):")
        )
        self.stdout.write(f"VITE_VAPID_PUBLIC_KEY={public_b64}")
