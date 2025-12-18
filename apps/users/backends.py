# apps/users/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Permite iniciar sesión usando:
    - correo institucional (email)
    - username
    - o la parte antes de @ del correo (itupacv de itupacv@unsa.edu.pe)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        username = username.strip()

        # Lista de posibles formas de buscar al usuario
        lookups = []

        # (1) Buscar por email exacto
        lookups.append({"email__iexact": username})

        # (2) Buscar por username exacto
        lookups.append({"username__iexact": username})

        # (3) Si parece un correo, probar con la parte antes de @ como username
        if "@" in username:
            local_part = username.split("@", 1)[0]
            lookups.append({"username__iexact": local_part})

        # Probar cada lookup hasta encontrar un usuario válido
        for lookup in lookups:
            try:
                user = UserModel.objects.get(**lookup)
            except UserModel.DoesNotExist:
                user = None

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None
