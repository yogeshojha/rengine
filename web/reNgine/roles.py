from rolepermissions.roles import AbstractUserRole
from reNgine.definitions import *

class Admin(AbstractUserRole):
    available_permissions = {
        ADD_MODIFY_USERS: True,
        ADD_MODIFY_SCAN_ENGINES: True,
        ADD_MODIFY_EXTERNAL_TOOLS: True,
        ADD_MODIFY_TARGET: True,
        ADD_MODIFY_SETTINGS: True,
        VIEW_DOWNLOAD_REPORT: True,
    }


class PenetrationTester(AbstractUserRole):
    available_permissions = {
        ADD_MODIFY_USERS: False,
        ADD_MODIFY_SCAN_ENGINES: True,
        ADD_MODIFY_EXTERNAL_TOOLS: True,
        ADD_MODIFY_TARGET: True,
        ADD_MODIFY_SETTINGS: True,
        VIEW_DOWNLOAD_REPORT: True,
    }


class Auditor(AbstractUserRole):
    available_permissions = {
        ADD_MODIFY_USERS: False,
        ADD_MODIFY_SCAN_ENGINES: False,
        ADD_MODIFY_EXTERNAL_TOOLS: False,
        ADD_MODIFY_TARGET: False,
        ADD_MODIFY_SETTINGS: False,
        VIEW_DOWNLOAD_REPORT: True,
    }
