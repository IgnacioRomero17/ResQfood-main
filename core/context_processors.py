from marketplace.services.reminders import pending_orders_expiring

def reminders_cp(request):
    count = 0
    try:
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            count = pending_orders_expiring(user=user).count()
    except Exception:
        count = 0
    return {"reminders_count": count}

