from django import forms
from devilry.apps.core.models import AssignmentGroup


class BulkForm(forms.Form):
    groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                       label="Bulktest:")


class TypedMultipleChoiceFieldWithoutChoices(forms.TypedMultipleChoiceField):
    def valid_value(self, value):
        """
        Override this, because it loops through choices and validate them
        we do not want to provide all possible choices as input, so we
        ignore this.
        """
        return True



class GroupIdsForm(forms.Form):
    """
    Form to get a list of group ids that we know the given 
    examiner user can access, and that we know is within
    the given assignment.

    WARNING: You can not use this to render a HTML form, only to parse the
    input from a form that you render yourself, typically a form with
    checkboxes with ``name="group_ids"``.
    """
    group_ids = TypedMultipleChoiceFieldWithoutChoices(
        required=True,
        coerce=int,
        widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.assignment = kwargs.pop('assignment')
        super(GroupIdsForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(GroupIdsForm, self).clean()
        group_ids = cleaned_data.get('group_ids')
        if group_ids:
            cleaned_groups = AssignmentGroup.objects.filter_examiner_has_access(self.user)\
                .filter(id__in=group_ids, parentnode=self.assignment)
            if set(cleaned_groups.values_list('id', flat=True)) != set(group_ids):
                # NOTE: Not translating - this should not be possible through the UI
                raise forms.ValidationError('One or more of the selected groups are not in {}, or groups where you lack examiner permissions.'.format(
                    self.assignment.get_path()))
            else:
                self.cleaned_groups = cleaned_groups
        return cleaned_data
