from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required

import examiner

urlpatterns = patterns('devilry.restful',
    url(r'^examiner/assignments/$',
        login_required(examiner.RestAssignments.as_view()),
        name='devilry-restful-examiner-assignments'),
    url(r'^examiner/groups/(?P<assignment_id>\d+)/$',
        login_required(examiner.RestGroups.as_view()),
        name='devilry-restful-examiner-groups'),
)
