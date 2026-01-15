from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organisation(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    org_type = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.get_username()


class NationalTarget(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class Indicator(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    national_target = models.ForeignKey(NationalTarget, on_delete=models.CASCADE, related_name="indicators")

    def __str__(self):
        return f"{self.code} - {self.title}"
