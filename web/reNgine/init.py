import logging
import secrets
import os

logger = logging.getLogger(__name__)


'''
Based on
https://github.com/MobSF/Mobile-Security-Framework-MobSF/blob/master/MobSF/init.py
'''


def first_run(secret_file, base_dir):
    if 'RENGINE_SECRET_KEY' in os.environ:
        secret_key = os.environ['RENGINE_SECRET_KEY']
    elif os.path.isfile(secret_file):
        secret_key = open(secret_file).read().strip()
    else:
        try:
            secret_key = get_random()
            secret = open(secret_file, 'w')
            secret.write(secret_key)
            secret.close()
        except OSError:
            raise Exception(f'Secret file generation failed. Path: {secret_file}')
    return secret_key


def get_random():
    charlist = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(charlist) for _ in range(64))
