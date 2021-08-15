import os
import random
import logging
import sys
import subprocess

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
        except IOError:
            raise Exception('Secret file generation failed' % secret_file)
    return secret_key



def get_random():
    choice = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join([random.SystemRandom().choice(choice) for i in range(50)])
