# Administrator guide (for the President and future teams)

Log in at `/admin/` (or your private ADMIN_URL). The dashboard home shows what needs attention and a gold
**＋ CREATE NEW EVENT** button.

## Create a new event (fun fair, seminar, dinner, anything)
1. Dashboard → **＋ CREATE NEW EVENT** (also on the Events list page).
2. Fill section **1 · The basics**: name, category, date & time, venue, short summary. Choose a status:
   *Draft* (hidden), *Published* (public), *Archived*.
3. Add a **cover image** and/or **poster** (section 2) and the description/purpose (section 3).
4. Optional: organizing team, registration details/link, "Feature on homepage", and **Schedule publication** (section 7).
5. Click **Save**. The event page, its URL (`/events/<name>/`), its category listing, its Upcoming/Past placement and its photo album
   are created automatically. After the date passes it moves to *Past events* by itself.
No HTML, CSS or Python is ever needed.

Other event tools (events list): tick events → *Action* menu → **Publish / Archive / Draft / Feature / Duplicate**. Use **Duplicate**
to reuse an event as a template for next year (copies details, highlights and speakers as a draft; photos are not copied).
New categories: **Events → Event categories → Add**.

## Upload event highlights, photos, videos, and publish a recap
Open the event, then:
- **Highlights & key activities** panel: add numbered highlights and activities (each can have an image).
- **Speakers / guests** panel: name, title, photo.
- **Event gallery** panel: add photos/videos one by one, **or** click **"Upload many photos at once →"** (section 7) to select dozens
  of photos together. They appear on the event page *and* in Gallery automatically — never upload twice.
  Videos: paste a YouTube/Vimeo link (recommended) or upload an MP4 (max 90 MB).
- **Recap** (section 6): write the headline and story after the event. As soon as a recap exists, the page switches to the
  editorial "Event story" layout. The event stays in the Past events archive forever.

## Team members
Dashboard → **Team members**. Drag rows to rearrange, then press **Save**; or edit the *order* number. Change the *category* in the
list to promote someone (e.g. Core Team → President and Leadership). Click a name to upload a photo, bio, program, class and links.
Without a photo a tasteful initials avatar is shown. When a new team takes over, add the new members with a new **Tenure**
(e.g. 2027-2028) and change the old ones' tenure — the old team moves to the *Leadership archive*.

## Announcements
**News & Announcements → Announcements → Add**. Choose Published, tick *Pinned* or *Featured on homepage*, set a future date to schedule it.

## Homepage, About, menus, footer, logo, colours, social links
- **Website → Homepage sections**: drag to reorder, tick/untick *Is visible*, open one to change its heading/text/image.
- **Website → About content blocks / Page texts**: vision, mission, objectives and values were drafted as **PENDING APPROVAL** and are
  **hidden from visitors** (you see them as a preview when logged in). Review, edit, then select them and run
  *Action → Mark selected as APPROVED* to publish.
- **Website → Menu links**: edit the top menu and footer links.
- **Website → Website settings**: logo, favicon, colours, contact details, social links, SEO, analytics ID, footer text, intro on/off,
  membership open/closed.

## Membership applications
**Membership → Membership applications**: search/filter, open one to add notes and set Approved/Rejected, or use bulk actions.
*Action → Export selected to CSV* downloads an Excel-readable file.

## Media library
**Media & Gallery → Media items**: every photo/video with filters; open an item to replace the file, edit the caption, move it to another
event/album, or delete it.

## Roles
Create staff accounts under **Users** and give them a group: *Website Administrator* (everything), *Content Editor* (events, team,
gallery, news, homepage text), *Membership Manager* (applications, messages). Tick **Staff status**. Hand over to the next President by
creating their account and deactivating yours.

## Backups
Run `python manage.py backup_site` (local) for a ZIP of data + media. On Render, enable the PostgreSQL backups described in DEPLOYMENT.md,
and keep Cloudinary as the home of your images.
