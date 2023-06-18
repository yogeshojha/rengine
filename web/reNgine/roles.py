from rolepermissions.roles import AbstractUserRole
from reNgine.definitions import *

class Admin(AbstractUserRole):
    available_permissions = {
        PERM_ADD_MODIFY_SYSTEM_SETTINGS: True,
        PERM_ADD_MODIFY_SCAN_SETTINGS: True,
        PERM_ADD_MODIFY_SCAN_ENGINES: True,
        PERM_ADD_MODIFY_EXTERNAL_TOOLS: True,
        PERM_ADD_MODIFY_TARGET: True,
        PERM_VIEW_DOWNLOAD_REPORT: True,
        PERM_INITATE_SCANS: True,
    }


class PenetrationTester(AbstractUserRole):
    available_permissions = {
        PERM_ADD_MODIFY_SYSTEM_SETTINGS: False,
        PERM_ADD_MODIFY_SCAN_SETTINGS: True,
        PERM_ADD_MODIFY_SCAN_ENGINES: True,
        PERM_ADD_MODIFY_EXTERNAL_TOOLS: True,
        PERM_ADD_MODIFY_TARGET: True,
        PERM_VIEW_DOWNLOAD_REPORT: True,
        PERM_INITATE_SCANS: True,
    }


class Auditor(AbstractUserRole):
    available_permissions = {
        PERM_ADD_MODIFY_SYSTEM_SETTINGS: False,
        PERM_ADD_MODIFY_SCAN_SETTINGS: False,
        PERM_ADD_MODIFY_SCAN_ENGINES: False,
        PERM_ADD_MODIFY_EXTERNAL_TOOLS: False,
        PERM_ADD_MODIFY_TARGET: False,
        PERM_VIEW_DOWNLOAD_REPORT: True,
        PERM_INITATE_SCANS: False,
    }
