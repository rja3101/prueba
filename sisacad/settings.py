LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/academics/offerings/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

INSTALLED_APPS += [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE += [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
