import os

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

if __name__ == '__main__':
    with open('/tmp/secret.txt', 'w') as f:
        f.write('testconfig')
    os.environ['SECRET_FILE'] = '/tmp/secret.txt'
    from reNgine import celery
    from reNgine.tasks import subdomain_discovery
    subdomain_discovery('jahmyst.synology.me', ctx={})