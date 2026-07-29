from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """Same algorithm as Django's default, fewer iterations.

    Tuned for hosts with very limited CPU (e.g. Render's free tier), where
    Django's current default iteration count makes password checks take
    several seconds. Still well above OWASP's minimum recommendation.
    """
    iterations = 320_000
