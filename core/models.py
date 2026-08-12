from django.contrib.auth.models import AbstractUser
from django.db import models
from rest_framework import permissions

class User(AbstractUser):
    class Roles(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        PARTNER  = "partner",  "Partner"
        ADMIN    = "admin",    "Admin"
    role  = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CUSTOMER)
    phone = models.CharField(max_length=30, blank=True)

