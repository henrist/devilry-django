import re

from django.contrib.auth import get_user_model
from django_cradmin import crinstance

from devilry.apps.core.models import Assignment
from devilry.devilry_examiner.cradminextensions import devilry_crmenu_examiner
from devilry.devilry_examiner.views.dashboard import assignmentlist


class Menu(devilry_crmenu_examiner.Menu):
    def build_menu(self):
        super(Menu, self).build_menu()
        self.add_role_menuitem_object()


class CrAdminInstance(crinstance.BaseCrAdminInstance):
    menuclass = Menu
    roleclass = Assignment
    apps = [
        ('assignmentlist', assignmentlist.App),
    ]
    id = 'devilry_examiner'
    rolefrontpage_appname = 'assignmentlist'
    flatten_rolefrontpage_url = True

    def get_rolequeryset(self):
        return get_user_model().objects.filter(id=self.request.user.id)

    def get_titletext_for_role(self, role):
        """
        Get a short title briefly describing the given ``role``.
        Remember that the role is a User.
        """
        return str(role.id)

    @classmethod
    def matches_urlpath(cls, urlpath):
        return re.match('/devilry_examiner/(\d+.*/)?$', urlpath) or \
            re.match('/devilry_examiner/\d+/filter/.*$', urlpath)