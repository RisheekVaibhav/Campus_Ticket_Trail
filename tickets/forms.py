from django import forms
from .models import Ticket


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            'category', 'subject', 'what_needs_to_be_done',
            'problem_description', 'submission_details',
            'student_stated_deadline', 'additional_info',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Unable to pay semester fees'}),
            'what_needs_to_be_done': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                'placeholder': 'Explain exactly what you need the administration to do.'}),
            'problem_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                'placeholder': 'Explain the problem you are facing.'}),
            'submission_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'placeholder': 'Where documents need to be submitted, portal info, requesting department, etc. (if relevant)'}),
            'student_stated_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'placeholder': 'Anything else relevant (optional).'}),
        }


class MoreInfoRequestForm(forms.Form):
    more_info_request = forms.CharField(
        label="What additional information is needed?",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
            'placeholder': 'e.g. Please upload a scanned copy of your previous semester fee receipt.'}),
    )


class StudentResponseForm(forms.Form):
    response = forms.CharField(
        label="Your response",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )


class ResolveForm(forms.Form):
    resolution_details = forms.CharField(
        label="Resolution details",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
            'placeholder': 'Explain how this was resolved.'}),
    )


class DeclineForm(forms.Form):
    decline_reason = forms.CharField(
        label="Reason for declining (required, shown to the student)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )


class InternalNoteForm(forms.Form):
    note = forms.CharField(
        label="Internal note",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class PriorityOverrideForm(forms.Form):
    from .models import PRIORITY_CHOICES
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    reason = forms.CharField(
        label="Reason for override (required, logged)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class ReassignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        from accounts.models import User
        qs = User.objects.filter(role='staff')
        if department:
            qs = qs.filter(department=department)
        self.fields['assigned_to'].queryset = qs
