try:
    import mercadopago  # type: ignore
except Exception:  # pragma: no cover
    mercadopago = None  # lazy-loaded / mocked in tests
from django.conf import settings
from decimal import Decimal
from json import dumps as json_dumps




def create_mp_preference(order):
    """
    Crea una Preferencia de Mercado Pago para un pedido.
    Devuelve: {
      'preference_id': str,
      'init_point': str | None,
      'sandbox_init_point': str | None,
    }
    """
    if mercadopago is None:
        raise RuntimeError("MercadoPago SDK not installed")

    sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    # 1) Resolver precio de forma segura (> 0)
    p = order.pack
    cand = [
        getattr(order, "precio_pagado", None),
        getattr(p, "precio_oferta", None),
        getattr(p, "precio", None),
    ]
    numeric_types = (int, float, Decimal)
    price = next((v for v in cand if isinstance(v, numeric_types) and float(v) > 0), None)
    if price is None:
        # Permite string numÃ©rica
        cand_str = next((v for v in cand if isinstance(v, str) and v.strip()), None)
        if cand_str is not None:
            try:
                val = float(cand_str)
                if val > 0:
                    price = val
            except ValueError:
                pass
    if price is None or float(price) <= 0:
        raise ValueError("Cannot create MP preference with non-positive price")

    items = [{
        "title": getattr(p, "titulo", "Item"),
        "quantity": 1,
        "unit_price": float(price),
        "currency_id": "ARS",
    }]

    # 2) Tomar URLs desde settings y quitar comillas accidentales
    def clean_url(s):
        s = (s or "").strip()
        if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
            s = s[1:-1].strip()
        return s

    success = clean_url(getattr(settings, "MP_BACK_URL_SUCCESS", ""))
    pending = clean_url(getattr(settings, "MP_BACK_URL_PENDING", ""))
    failure = clean_url(getattr(settings, "MP_BACK_URL_FAILURE", ""))

    back_urls = {k: v for k, v in {
        "success": success,
        "pending": pending,
        "failure": failure,
    }.items() if v}

    pref_body = {
        "items": items,
        "external_reference": str(order.id),
        "back_urls": back_urls,
    }

    # auto_return SOLO si hay success real; usar solo con https para evitar 400 en dev/local
    success_url = back_urls.get("success")
    if success_url and success_url.startswith("https://"):
        pref_body["auto_return"] = "approved"

    # notification_url SOLO si es publica (no localhost ni placeholder)
    notif = clean_url(getattr(settings, "MP_NOTIFICATION_URL", ""))
    if notif.startswith("http") and "localhost" not in notif and "example.com" not in notif:
        pref_body["notification_url"] = notif

    # (Opcional) log DEV
    import logging
    logging.getLogger(__name__).info(
        "MP pref body: success=%s pending=%s failure=%s auto_return=%s price=%.2f",
        bool(back_urls.get("success")), bool(back_urls.get("pending")),
        bool(back_urls.get("failure")), pref_body.get("auto_return"), float(price)
    )
    import logging
    logging.getLogger(__name__).info("MP pref body: %s", pref_body)

    print("DEBUG MP back_urls:", back_urls)
    print("DEBUG MP pref_body:", json_dumps(pref_body, ensure_ascii=False))
    resp = sdk.preference().create(pref_body)
    data = resp.get("response", {}) if isinstance(resp, dict) else {}
    # If Mercado Pago returned an error payload or missing id, surface a clear message
    if isinstance(resp, dict):
        status = resp.get("status")
        if not data.get("id"):
            mp_msg = ""
            if isinstance(data, dict):
                mp_msg = data.get("message") or data.get("error_description") or data.get("error") or ""
            if status and int(status) >= 400:
                raise ValueError(mp_msg or f"MercadoPago preference creation failed (status {status})")
            # No id and no explicit status, still fail clearly
            if not data.get("id"):
                raise ValueError(mp_msg or "MercadoPago preference creation failed")
    return {
        "preference_id": data.get("id"),
        "init_point": data.get("init_point"),
        "sandbox_init_point": data.get("sandbox_init_point"),
    }
