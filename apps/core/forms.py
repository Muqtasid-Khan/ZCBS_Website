from django import forms

from .models import ContactSubmission, NewsletterSubscriber


class StyledFormMixin:
    def _style(self):
        for name, f in self.fields.items():
            w = f.widget
            if isinstance(w, (forms.CheckboxSelectMultiple, forms.CheckboxInput)):
                continue
            w.attrs.setdefault("class", "form-select" if isinstance(w, forms.Select) else "form-control")


class HoneypotMixin(StyledFormMixin, forms.Form):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()

    website = forms.CharField(required=False, widget=forms.TextInput(
        attrs={"tabindex": "-1", "autocomplete": "off", "class": "hp-field", "aria-hidden": "true"}))

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class ContactForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "subject", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 6})}


class NewsletterForm(HoneypotMixin, forms.Form):
    email = forms.EmailField()
