# Event registration system (all events)

One reusable system, built into the existing Django site (`apps/registrations/`). Every event — already published or created later — has its own **registration settings** row (created automatically). Nothing is hard-coded to one event.

## Setup
```
pip install -r requirements.txt        # adds openpyxl
python manage.py migrate               # creates tables, attaches settings to every existing event, creates 4 roles
```
`build.sh` already runs `migrate` on Render. Run it **before** the new code starts serving, or saving an event will fail.
Optional trial data: `python manage.py seed_registration_demo` (fictional) / `--remove`.

## Per-event ON/OFF switch
Dashboard → **Events → open an event → "Built-in registration & ticketing"** (or Registration settings list, which has tick-boxes for every event at once).
* **Use the built-in registration system** – OFF keeps the event's old registration box/link exactly as before. Existing events start OFF; brand-new events start ON (unless you typed an external link).
* **Enable CASPAM Student Verification and Special Ticket Pricing** – independent per event, OFF by default. Cannot be saved ON without a dataset.
  * ON: participants choose *CASPAM student* or *External*. CASPAM claims are verified; prices come from `caspam_price` / `external_price` (Qawwali Night: 1,500 / 2,000).
  * OFF: no CASPAM question, no roll number, no dataset matching, no CASPAM price; the event uses `standard_price` (0 = free).
Quick route for one event: `python manage.py configure_registration <slug> --caspam --dataset <id> --caspam-price 1500 --external-price 2000`.

## Registration form per event
Name and email are always asked (email is needed to return to the pass). Contact number: required / optional / not asked. Add any questions in *Registration settings → Extra questions* (text, long text, number, drop-down, tick box, email, phone; required or optional; reorder; hide). `cnic` cannot be added as an ordinary field.

## Student verification workflow (CASPAM ON only)
1. Admin uploads a `.csv`/`.xlsx` (columns: roll number, name, optional CNIC, WhatsApp/mobile) under *CASPAM student datasets*. The file is parsed in memory and **not kept**; CNIC and mobile are stored only as keyed hashes (last 2–4 digits for masked display). Use fictional data until you decide otherwise.
2. A participant who claims CASPAM enters roll number + the "second identifier" chosen for the event (mobile by default; CNIC only if you select it; none possible).
3. Server rules: roll must exist **and** name must match **and** second identifier must match → *Verified* (CASPAM price). Roll not found → *Not verified* (external price). Roll found but name/second identifier conflict, or no dataset → *Pending review* (external price shown as provisional; payment instructions and approval wait).
4. Event Manager approves/rejects in *Registrations* (actions). Approve → CASPAM price; reject → external.
A name alone never verifies anyone. The submitted CNIC is never stored.

## Payment workflow
Statuses: Unpaid → Payment Submitted → Under Review → Paid / Rejected (resubmit allowed) → Refunded; "Free" for 0-price events. Participants submit method + transaction ID only; **only the Finance Manager/Super Admin can mark Paid** (dashboard actions). Price is always computed on the server. Payment methods are manual instructions (bank, Easypaisa, JazzCash, cash). **No online gateway is integrated.**

## What the participant sees (status table)
On their private registration page: **Pending** (waiting for payment or for your team to check the receipt) → **Registered** (you approved the payment) or **Payment not received** with your message (default: "Sorry, we didn't get your payment. For queries, please contact our team. Thank you."; editable per event in Registration settings). Finance changes it with the dashboard actions *Payment → APPROVE* / *REJECT*.

## Live pass and check-in
* Pass lives on the participant's private page `/registrations/my/<random token>/` (no personal data in the URL, `no-store`, `noindex`). Shows event, name, reference, live status and a unique code `XXXXX-XXXXX`; no download, no QR, no PDF/image.
* Active only when: not cancelled, verification not pending, payment Paid/Free, not revoked. Admins can revoke/restore.
* Staff screen `/registrations/staff/checkin/` (Check-in Staff role): choose event, enter code → sees exists / paid / eligible / active / already used → **Admit**. Admit is one conditional database UPDATE (`checked_in_at IS NULL`), so a code can enter once; the second attempt says ALREADY USED. The participant's pass flips to "Used" within ~15 s.
* Screenshots cannot be prevented; protection is the server-side one-time check.

## Roles (Dashboard → Users → Groups; tick "Staff status" for anyone who signs in)
| Role | Can do |
|---|---|
| Super Admin | everything, incl. audit log |
| Event Manager | event settings, form questions, payment methods, datasets, verification reviews, pass revoke, view/export |
| Finance Manager | view registrations, approve/reject/refund payments, export |
| Check-in Staff | check-in screen only |
Every action is checked on the server and written to *Audit log*.

## Dashboard and Excel export
`/registrations/staff/dashboard/` (also linked on the dashboard home): per event – switch status, registered, paid, needing review, entered, revenue, and six `.xlsx` exports: All, Verified CASPAM students, External, Paid, Pending, Checked-in. Headings, filters, frozen header + first two columns, widths, colour-coded statuses. No CNIC is ever stored or exported; cells starting with `= + - @` are neutralised.

## Not included / needs you
Payment gateway (needs merchant credentials), SMS/WhatsApp/email delivery of the pass link (email needs `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`; currently the participant sees the link right after registering — it is not emailed), screenshot upload of payment proof, rate limits are per server process (use a shared cache such as Redis if you run several instances).
