import io
import os
import random
import time
from urllib.parse import quote_plus

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from marketplace.models import Pack, Partner

PICSUM_URL = "https://picsum.photos"
UNSPLASH_SOURCE = "https://source.unsplash.com"

DEFAULT_PACK_QUERIES = [
    "food", "breakfast", "lunch", "dinner",
    "bakery", "fruits", "vegetables", "meat",
    "coffee", "pizza", "pasta", "supermarket"
]

DEFAULT_PARTNER_QUERIES = [
    "storefront", "shop", "grocery store", "cafe", "butcher shop", "bakery shop"
]


def ensure_media_dir():
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        raise CommandError("MEDIA_ROOT no estÃ¡ configurado en settings.")
    os.makedirs(media_root, exist_ok=True)


def fetch_image(url, timeout=20):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def placeholder_bytes():
    """
    Devuelve bytes de placeholder. Si existe static/img/placeholder-pack.svg lo usa,
    sino genera un PNG 1x1 gris claro.
    """
    static_path = os.path.join(getattr(settings, "BASE_DIR", os.getcwd()), "static", "img", "placeholder-pack.svg")
    if os.path.exists(static_path):
        with open(static_path, "rb") as f:
            return f.read()
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (1, 1), (240, 240, 240, 255)).save(buf, format="PNG")
    return buf.getvalue()


def picsum_url(w=1200, h=900, seed=None):
    seed = seed or random.randint(1, 10000)
    return f"{PICSUM_URL}/seed/{seed}/{w}/{h}"


def unsplash_random(query="food", w=1200, h=900):
    q = quote_plus(query)
    return f"{UNSPLASH_SOURCE}/random/{w}x{h}/?{q}"


def attach_image_to_instance(instance, field_name, image_bytes, filename):
    django_file = ContentFile(image_bytes, name=filename)
    getattr(instance, field_name).save(filename, django_file, save=True)


class Command(BaseCommand):
    help = "Importa imÃ¡genes demo para Packs y Partners (logos) desde Picsum/Unsplash o placeholder local."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=32, help="MÃ¡ximo de packs a procesar (default 32).")
        parser.add_argument("--force", action="store_true", help="Reemplazar imÃ¡genes ya existentes.")
        parser.add_argument(
            "--source", choices=["picsum", "unsplash", "local"], default="picsum",
            help="Fuente de imÃ¡genes: picsum|unsplash|local (default picsum).",
        )
        parser.add_argument("--query", type=str, default="", help="Query para Unsplash (p.ej. 'bakery, coffee').")
        parser.add_argument("--partners", action="store_true", help="TambiÃ©n asignar logos a Partner.")
        parser.add_argument("--sleep", type=float, default=0.5, help="Delay entre descargas para evitar rate-limit.")
        parser.add_argument("--width", type=int, default=1200)
        parser.add_argument("--height", type=int, default=900)

    def handle(self, *args, **opts):
        ensure_media_dir()

        limit = opts["limit"]
        force = opts["force"]
        source = opts["source"]
        q = (opts["query"] or "").strip()
        do_partners = opts["partners"]
        slp = float(opts["sleep"])
        W, H = int(opts["width"]), int(opts["height"])

        self.stdout.write(self.style.MIGRATE_HEADING(f"Fuente: {source}  Â·  LÃ­mite packs: {limit}  Â·  Force: {force}"))

        # PARTNERS (logos cuadrados)
        if do_partners:
            partners = Partner.objects.all()
            self.stdout.write(self.style.NOTICE(f"Asignando logos a {partners.count()} comercios..."))
            for partner in partners:
                img_field = getattr(partner, "imagen", None)
                has_img = bool(img_field and getattr(img_field, "name", ""))
                if has_img and not force:
                    continue
                try:
                    if source == "picsum":
                        url = picsum_url(600, 600, seed=partner.id)
                        img = fetch_image(url)
                    elif source == "unsplash":
                        query = q or random.choice(DEFAULT_PARTNER_QUERIES)
                        url = unsplash_random(query, 600, 600)
                        resp = requests.get(url, allow_redirects=True, timeout=20)
                        resp.raise_for_status()
                        img = resp.content
                    else:
                        img = placeholder_bytes()

                    fname = f"partner_{partner.id}.jpg"
                    attach_image_to_instance(partner, "imagen", img, fname)
                    self.stdout.write(self.style.SUCCESS(f"âœ“ Partner {partner.id} Â· {partner.nombre}"))
                    time.sleep(slp)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"âœ— Partner {partner.id} Â· {e}"))
                    try:
                        attach_image_to_instance(partner, "imagen", placeholder_bytes(), f"partner_{partner.id}_ph.png")
                        self.stdout.write(self.style.WARNING("  â†’ placeholder asignado"))
                    except Exception:
                        pass

        # PACKS
        try:
            packs_qs = Pack.objects.all().order_by("-created_at")[:limit]
        except Exception:
            packs_qs = Pack.objects.all().order_by("-id")[:limit]
        self.stdout.write(self.style.NOTICE(f"Procesando {packs_qs.count()} packs..."))

        for p in packs_qs:
            img_field = getattr(p, "imagen", None)
            has_img = bool(img_field and getattr(img_field, "name", ""))
            if has_img and not force:
                continue
            try:
                if source == "picsum":
                    url = picsum_url(W, H, seed=p.id)
                    img = fetch_image(url)
                elif source == "unsplash":
                    base_q = q or (getattr(p.partner, "nombre", "") or getattr(p, "titulo", "") or "food")
                    base_q = (base_q or "food").split()[0]
                    url = unsplash_random(base_q, W, H)
                    resp = requests.get(url, allow_redirects=True, timeout=25)
                    resp.raise_for_status()
                    img = resp.content
                else:
                    img = placeholder_bytes()

                fname = f"pack_{p.id}.jpg"
                attach_image_to_instance(p, "imagen", img, fname)
                self.stdout.write(self.style.SUCCESS(f"âœ“ Pack {p.id} Â· {getattr(p, 'titulo', '')}"))
                time.sleep(slp)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"âœ— Pack {p.id} Â· {e}"))
                try:
                    attach_image_to_instance(p, "imagen", placeholder_bytes(), f"pack_{p.id}_ph.png")
                    self.stdout.write(self.style.WARNING("  â†’ placeholder asignado"))
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS("âœ… ImportaciÃ³n de imÃ¡genes demo finalizada."))


