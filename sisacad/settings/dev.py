from .base import *

DEBUG = True

# Solo redirecciones de login/logout
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/academics/offerings/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Backend de autenticación: correo institucional o username
AUTHENTICATION_BACKENDS = [
    "apps.users.backends.EmailOrUsernameBackend",
]
