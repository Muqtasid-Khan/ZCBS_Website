import re

from django import forms

from . import utils
from .models import EventRegistrationConfig, PaymentMethod, RegistrationField


def _w(cls="form-control", **attrs):
    return {"class": cls, **attrs}


class RegistrationForm(forms.Form):
    """Built from the event's own configuration. CASPAM fields exist ONLY when the event has
    CASPAM verification switched on; otherwise the form never mentions them."""
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))  # honeypot
    full_name = forms.CharField(label="Full name", max_length=150, widget=forms.TextInput(attrs=_w(autocomplete="name")))
    email = forms.EmailField(label="Email", max_length=254, widget=forms.EmailInput(attrs=_w(autocomplete="email")))

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        if config.phone_mode != config.PH_HIDE:
            self.fields["phone"] = forms.CharField(
                label="Contact number (WhatsApp preferred)", max_length=20, required=config.phone_mode == config.PH_REQ,
                widget=forms.TextInput(attrs=_w(autocomplete="tel", inputmode="tel")))
        if config.uses_caspam:
            self.fields["participant_type"] = forms.ChoiceField(
                label="Registering as", choices=[("caspam", f"CASPAM student — PKR {config.caspam_price:,.0f} (verification required)"),
                                                 ("external", f"External participant — PKR {config.external_price:,.0f}")],
                widget=forms.RadioSelect(attrs={"class": "form-check-input"}))
            self.fields["caspam_roll"] = forms.CharField(label="CASPAM roll number", max_length=40, required=False, widget=forms.TextInput(attrs=_w()))
            if config.second_factor == config.SF_MOBILE:
                self.fields["second_factor"] = forms.CharField(label="Your WhatsApp/mobile number as registered with CASPAM", max_length=20, required=False,
                                                               widget=forms.TextInput(attrs=_w(inputmode="tel")))
            elif config.second_factor == config.SF_CNIC:
                self.fields["second_factor"] = forms.CharField(label="CNIC (used only for matching, never stored)", max_length=15, required=False,
                                                               widget=forms.TextInput(attrs=_w(inputmode="numeric", autocomplete="off")))
        self.custom = []
        for f in config.fields.filter(is_active=True):
            name = f"f_{f.key}"
            self.fields[name] = self._build(f)
            self.custom.append(name)

    @staticmethod
    def _build(f):
        kw = {"label": f.label, "required": f.required, "help_text": f.help_text}
        t = f.field_type
        if t == RegistrationField.LONG:
            return forms.CharField(max_length=1000, widget=forms.Textarea(attrs=_w(rows=3)), **kw)
        if t == RegistrationField.NUMBER:
            return forms.DecimalField(max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs=_w()), **kw)
        if t == RegistrationField.CHOICE:
            ch = [("", "— choose —")] + [(c, c) for c in f.choice_list]
            return forms.ChoiceField(choices=ch, widget=forms.Select(attrs=_w("form-select")), **kw)
        if t == RegistrationField.CHECK:
            return forms.BooleanField(widget=forms.CheckboxInput(attrs=_w("form-check-input")), **kw)
        if t == RegistrationField.EMAIL:
            return forms.EmailField(widget=forms.EmailInput(attrs=_w()), **kw)
        if t == RegistrationField.TEL:
            return forms.CharField(max_length=20, widget=forms.TextInput(attrs=_w(inputmode="tel")), **kw)
        return forms.CharField(max_length=200, widget=forms.TextInput(attrs=_w()), **kw)

    def clean_full_name(self):
        v = " ".join(self.cleaned_data["full_name"].split())
        if len(v) < 3:
            raise forms.ValidationError("Please enter your full name.")
        return v

    def clean_phone(self):
        v = self.cleaned_data.get("phone", "").strip()
        if v and len(utils.digits(v)) < 10:
            raise forms.ValidationError("Enter a valid phone number.")
        return v

    def clean(self):
        d = super().clean()
        if self.config.uses_caspam and d.get("participant_type") == "caspam":
            if not utils.normalize_roll(d.get("caspam_roll", "")):
                self.add_error("caspam_roll", "Enter your CASPAM roll number.")
            sf = d.get("second_factor", "")
            if self.config.second_factor == self.config.SF_MOBILE and len(utils.digits(sf)) < 10:
                self.add_error("second_factor", "Enter the mobile number registered with CASPAM.")
            if self.config.second_factor == self.config.SF_CNIC and len(utils.digits(sf)) != 13:
                self.add_error("second_factor", "Enter a 13-digit CNIC.")
        return d

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class PaymentForm(forms.Form):
    method = forms.ModelChoiceField(queryset=PaymentMethod.objects.none(), label="Payment method", empty_label="— choose —",
                                    widget=forms.Select(attrs=_w("form-select")))
    reference = forms.CharField(label="Transaction ID / receipt number", max_length=80, widget=forms.TextInput(attrs=_w()))
    note = forms.CharField(label="Note (optional)", required=False, max_length=300, widget=forms.TextInput(attrs=_w()))

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["method"].queryset = config.payment_methods.filter(is_active=True)

    def clean_reference(self):
        v = self.cleaned_data["reference"].strip()
        if len(v) < 4 or not re.search(r"[A-Za-z0-9]", v):
            raise forms.ValidationError("Enter the transaction ID or receipt number.")
        return v


class LookupForm(forms.Form):
    reference = forms.CharField(label="Registration reference", max_length=20, widget=forms.TextInput(attrs=_w(placeholder="ZR-XXXXXXX")))
    email = forms.EmailField(label="Email used to register", widget=forms.EmailInput(attrs=_w()))


class CheckInForm(forms.Form):
    code = forms.CharField(label="Verification code", max_length=16, widget=forms.TextInput(attrs=_w(
        autofocus=True, autocomplete="off", autocapitalize="characters", placeholder="XXXXX-XXXXX")))
    event = forms.ModelChoiceField(queryset=None, label="Event", empty_label="— choose the event —",
                                   widget=forms.Select(attrs=_w("form-select")))

    def __init__(self, events, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = events
