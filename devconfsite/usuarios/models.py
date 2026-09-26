from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, name, password, **extra_fields):
        if not email:
            raise ValueError("The email is required.")
        usuario = self.model(email=self.normalize_email(email).lower(), name=name, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("role", Usuario.Role.CLIENTE)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, name, password, **extra_fields)

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("role", Usuario.Role.ADMIN)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["role"] != Usuario.Role.ADMIN:
            raise ValueError("A superuser must have the admin role.")
        return self._create_user(email, name, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ADMIN = "admin", "Admin"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField("password", max_length=128, db_column="password_hash")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENTE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="admins_creados"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        return self.role == self.Role.ADMIN

    def has_perm(self, perm, obj=None):
        return (self.is_active and self.is_staff) or super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return (self.is_active and self.is_staff) or super().has_module_perms(app_label)

    @property
    def is_blocked(self):
        return self.status == self.Status.BLOCKED
