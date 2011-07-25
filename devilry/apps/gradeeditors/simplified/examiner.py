from devilry.simplified import (SimplifiedModelApi, simplified_modelapi,
                                FieldSpec, PermissionDenied)
from ..models import Config, FeedbackDraft


@simplified_modelapi
class SimplifiedConfig(SimplifiedModelApi):
    class Meta:
        model = Config
        resultfields = FieldSpec('id', 'gradeeditorid', 'assignment', 'config')
        searchfields = FieldSpec()
        methods = ('read')

    #@classmethod
    #def write_authorize(cls, user, obj):
        #if not obj.assignment.can_save():
            #raise PermissionDenied()



@simplified_modelapi
class SimplifiedFeedbackDraft(SimplifiedModelApi):
    class Meta:
        model = FeedbackDraft
        resultfields = FieldSpec('id', 'delivery', 'saved_by', 'shared', 'draft')
        searchfields = FieldSpec()
        methods = ('create', 'read', 'update')

    @classmethod
    def write_authorize(cls, user, obj):
        if not obj.delivery.deadline.assignment_group.can_save():
            raise PermissionDenied()
