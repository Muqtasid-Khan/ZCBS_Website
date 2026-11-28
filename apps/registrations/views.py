from django.contrib import messages
from django.contrib.admin import site as admin_site
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.events.models import Event
from . import exports, services, utils
from .forms import CheckInForm, LookupForm, PaymentForm, RegistrationForm
from .models import AuditLog, Registration

NO_STORE = never_cache


def _event_or_404(request, slug):
    ev = get_object_or_404(Event.objects.select_related("reg_config", "category"), slug=slug)
    if not ev.is_visible and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404
    return ev


def _private(resp):
    """Pages that show personal data: never cached, never indexed, never leak the address."""
    resp["Cache-Control"] = "no-store, private"
    resp["X-Robots-Tag"] = "noindex, nofollow"
        resp["Referrer-Policy"] = "same-origin"
    return resp


def register(request, slug):
    ev = _event_or_404(request, slug)
    cfg = ev.reg_config
    if not cfg.builtin_enabled:
        return redirect(ev.get_absolute_url())
    open_ = services.can_register(ev)
    form = RegistrationForm(cfg, request.POST or None) if open_ else None
    if request.method == "POST" and open_:
        if utils.throttled(request, "register", 15):
            messages.error(request, "Too many attempts from this connection. Please wait a little and try again.")
        elif form.is_valid():
            try:
                reg = services.create_registration(ev, form.cleaned_data, request)
            except services.RegistrationError as exc:
                form.add_error(None, str(exc))
            else:
                return redirect("registrations:mine", token=reg.access_token)
    return _private(render(request, "registrations/register.html", {
        "event": ev, "cfg": cfg, "form": form, "open": open_, "full": cfg.is_full}))


@NO_STORE
def mine(request, token):
    reg = get_object_or_404(Registration.objects.select_related("event", "event__reg_config", "payment_method"), access_token=token)
    cfg = reg.event.reg_config
    pay_form = None
    if request.method == "POST" and request.POST.get("action") == "payment":
        pay_form = PaymentForm(cfg, request.POST)
        if utils.throttled(request, "payment", 20):
            messages.error(request, "Too many attempts. Please wait a little.")
        elif pay_form.is_valid():
            try:
                services.submit_payment(reg, pay_form.cleaned_data["method"], pay_form.cleaned_data["reference"],
                                        pay_form.cleaned_data["note"], request)
                messages.success(request, "Payment details received. The finance team will review them.")
                return redirect("registrations:mine", token=token)
            except services.RegistrationError as exc:
                pay_form.add_error(None, str(exc))
    elif reg.payment_instructions_visible:
        pay_form = PaymentForm(cfg)
    ctx = {"reg": reg, "event": reg.event, "cfg": cfg, "pay_form": pay_form,
           "methods": cfg.payment_methods.filter(is_active=True), "blockers": reg.pass_blockers()}
    return _private(render(request, "registrations/mine.html", ctx))


@NO_STORE
def pass_status(request, token):
    """Tiny JSON endpoint the live pass polls so a used/revoked pass flips instantly. No personal data."""
    reg = get_object_or_404(Registration, access_token=token)
    return _private(JsonResponse({"status": reg.pass_status}))


def lookup(request):
    form = LookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if utils.throttled(request, "lookup", 10):
            messages.error(request, "Too many attempts. Please wait a little.")
        else:
            reg = Registration.objects.filter(reference=form.cleaned_data["reference"].strip().upper(),
                                              email=form.cleaned_data["email"].strip().lower()).first()
            if reg:
                return redirect("registrations:mine", token=reg.access_token)
            messages.error(request, "We could not find a registration with those details.")
    return _private(render(request, "registrations/lookup.html", {"form": form}))


# ------------------------------------------------------------------ staff
def _events_for_staff():
    return Event.objects.filter(reg_config__builtin_enabled=True).order_by("-start_at")


@login_required
@permission_required("registrations.perform_checkin", raise_exception=True)
def checkin(request):
    form = CheckInForm(_events_for_staff(), request.POST or None, initial={"event": request.GET.get("event")})
    result = None
    if request.method == "POST" and form.is_valid():
        if utils.throttled(request, "checkin", 900, ident=f"u{request.user.pk}"):
            messages.error(request, "Too many look-ups. Please wait a moment.")
        else:
            ev, code = form.cleaned_data["event"], form.cleaned_data["code"]
            if request.POST.get("do") == "admit":
                ok, msg, reg = services.check_in(code, request.user, ev, request)
                result = {"admitted": ok, "message": msg, "reg": reg, "checks": services.inspect_code(code, ev)[1]}
            else:
                reg, checks = services.inspect_code(code, ev)
                AuditLog.record("checkin_lookup", request, detail=code[:12])
                result = {"reg": reg, "checks": checks, "can_admit": bool(reg) and all(ok for ok, _ in checks)}
    return _private(render(request, "registrations/checkin.html", {"form": form, "result": result}))


@login_required
@permission_required("registrations.view_dashboard", raise_exception=True)
def dashboard(request):
    rows = []
    for ev in Event.objects.select_related("reg_config", "category").order_by("-start_at", "-created_at"):
        cfg = ev.reg_config
        s = ev.registrations.aggregate(
            total=Count("id", filter=~Q(state="cancelled")),
            paid=Count("id", filter=Q(payment_status__in=["paid", "not_required"]) & ~Q(state="cancelled")),
            review=Count("id", filter=Q(verification_status="pending_review") & ~Q(state="cancelled")),
            in_=Count("id", filter=Q(checked_in_at__isnull=False)),
            revenue=Sum("price", filter=Q(payment_status="paid")))
        rows.append({"event": ev, "cfg": cfg, "s": s})
    ctx = {**admin_site.each_context(request), "rows": rows, "title": "Event registrations", "kinds": exports.KINDS}
    return render(request, "registrations/dashboard.html", ctx)


@login_required
@permission_required("registrations.export_registrations", raise_exception=True)
def export(request, event_id, kind):
    if kind not in exports.KINDS:
        raise Http404
    ev = get_object_or_404(Event.objects.select_related("reg_config"), pk=event_id)
    data, n = exports.build_workbook(ev, kind)
    AuditLog.record("export", request, event=ev, detail=f"{kind}: {n} rows")
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{exports.filename(ev, kind)}"'
    resp["Cache-Control"] = "no-store"
    return resp
