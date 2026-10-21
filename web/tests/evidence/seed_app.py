"""Create the throwaway operator account and project used by the UI harness.

Run by ``test_ui_evidence`` through the application's own settings, in its own
process, against the temporary cluster that harness started. Values arrive in
the environment so the password never appears in a process listing, and the
account is only ever created inside a database that is deleted afterwards.
"""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from dashboard.models import Project

    username = os.environ['ORCA_EVIDENCE_USER']
    password = os.environ['ORCA_EVIDENCE_PASSWORD']
    slug = os.environ['ORCA_EVIDENCE_SLUG']

    user, _ = get_user_model().objects.get_or_create(username=username)
    user.email = 'evidence@example.invalid'
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.set_password(password)
    user.save()
    Project.objects.get_or_create(
        slug=slug,
        defaults={'name': 'OrcaRouter Evidence', 'insert_date': timezone.now()})
    return 0


if __name__ == '__main__':
    sys.exit(main())
