from django import forms

from apps.core.forms import HoneypotMixin
from .models import InterestArea, MembershipApplication


class ApplicationForm(HoneypotMixin, forms.ModelForm):
    interests = forms.ModelMultipleChoiceField(queryset=InterestArea.objects.none(), required=False,
                                               widget=forms.CheckboxSelectMultiple, label="Areas of interest")

    class Meta:
        model = MembershipApplication
        fields = ["full_name", "registration_number", "program", "semester", "email", "phone",
                  "interests", "other_interests", "reason"]
        widgets = {"reason": forms.Textarea(attrs={"rows": 5})}
        labels = {"other_interests": "Anything else you are interested in? (optional)"}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["interests"].queryset = InterestArea.objects.filter(is_active=True)

    def clean_registration_number(self):
        v = self.cleaned_data["registration_number"].strip()
        if MembershipApplication.objects.filter(registration_number__iexact=v, status="pending").exists():
            raise forms.ValidationError("An application with this registration number is already awaiting review.")
        return v

    def clean_phone(self):
        v = self.cleaned_data["phone"].strip()
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError("Enter a valid contact number.")
        return v
