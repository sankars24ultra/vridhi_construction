# 1. Getting Started

[Documentation home](README.md)

## Who uses Vridhi?

Vridhi brings project purchasing, materials, client receipts, labor records, and
account administration into one workspace. A user's actual responsibilities are
defined by assigned projects and module/action permissions, not a job-title role.

## First installation versus everyday login

An empty database is seeded at backend startup, including an initial
`administrator` account and synthetic sample data. An installed machine connected
to an existing database uses that database's existing accounts; it does not create
a separate set of users merely because the computer changed.

Obtain the initial credential through your installation administrator. The
bootstrap configuration contains an Argon2id hash, not a recoverable plaintext
password. Existing users are not overwritten by first-run seeding. See
[operations](08-operations-and-troubleshooting.md) for installation details.

## Sign in

### Standalone public website on Netlify

`apps/website` is an independently installable public-site application. It contains
only the approved company website and branding, without the header Login, Team
Workspace section, ERP screens, API client, client-log sender or backend proxy.
The existing `apps/frontend` ERP application is unchanged. This standalone copy
can be deployed from its own repository; it does not import files outside its
folder. Website changes must be applied to the appropriate copy deliberately.

Use Node 24, then run `npm ci` and `npm run build` in `apps/website`.
For a Git-connected Netlify deployment, set **Base directory** to `apps/website`
when using the construction project as repository root, **Build command** to
`npm run build`, and **Publish directory** to `dist` (relative to the base).
If the website folder is its own repository, leave Base directory empty.
Its `netlify.toml` pins Node 24 and supplies the build settings.
For manual deployment, upload only the built `apps/website/dist` folder to Netlify
Drop, not the construction project, database, backups, `.env`, or source folder.
The build includes a Netlify `_headers` file with static-site security headers.
No SPA catch-all or API forwarding rule is included; `/app` and `/api` do not
provide an ERP or backend on this deployment.

`npm run dev` uses port 5174; `npm run preview` serves the production build on
port 4174. Theme switching, navigation, project choices, Journey and policy dialogs
remain local browser interactions. Replace the masked phone and `.example` email
before publication, and review hosting-specific privacy wording. Configure the
public domain and HTTPS in Netlify separately. Deploy and secure the ERP on its
own infrastructure/domain; this split does not fix its pending authorization issues.

The approved company homepage is the default entry page at `/`.
The hero pairs a filled "Let's shape your vision" button with an outlined
"Explore our services" button, using matching height, typography and spacing.
The retired `/website-preview` and `/?readability=preview` links redirect to `/`.
The footer uses the same logo-derived VRIDHI wordmark as the expanded sidebar.
It includes the tagline, a current-year copyright notice, Privacy Policy and
Terms of Use buttons, and a Contact section link. Policy
buttons open keyboard-accessible native dialogs with an icon-only close button
and Escape support. Titles and close controls remain visible while the policy
body scrolls independently; the body also supports keyboard scrolling.
The notices contain concise visitor-facing information about the planning guide,
browser storage, sample contact channels, technical information, workspace cookies,
project agreements and content rights, without internal draft/launch instructions.
They still require review against actual business and deployment practices before
public launch; they are not a claim of legal compliance. Sample contact labels
remain visible; no consent banner is added.
The website uses the application's blue-and-slate day palette: blue actions,
slate text, pale blue highlights and light neutral surfaces. Website styling is
scoped separately and does not change the application's theme.
The header's Day/Night switch changes the entire website and remembers the
choice in this browser. The login/application uses its saved theme first; if none
exists, it inherits the website theme on first opening. Subsequent website changes
do not overwrite the saved application choice. These preferences are browser-local,
not account settings synced across devices or separate users sharing a browser.
The website switch also sets
the hero illustration to daylight/dusk; the illustration's own toggle can still
be used independently. Both "trust" and "futures" use the same italic accent style.
The hero's building and sky layers gently follow mouse movement and return to
rest on pointer exit. Touch devices and reduced-motion mode omit this movement.
Its Login links open `/app` (the existing application) in a new tab. If already signed
in, the existing session continues; otherwise the usual login screen appears.
This local implementation does not publish the app online. Public deployment
still requires hosting, domain/DNS, HTTPS and a review of production settings.
No private project records are shown. Sample contact details remain clearly labelled.
The website includes a daylight/dusk concept illustration toggle, selectable
service details, an interactive four-stage approach and expandable visitor FAQs.
The approved About Vridhi section at `#about` uses the client-focused headline
"Your vision. Thoughtfully brought together." The comparison version and original
copy have been replaced by this single section.
Each journey selection (01 Discover, 02 Design, 03 Build, 04 Deliver) displays
its own original SVG concept illustration, activities, intended outcome and
client involvement. Illustrations are not actual project photographs, and the
proposed process remains subject to the agreed project scope.
Motion effects respect the visitor's reduced-motion preference. The illustration
is a concept, not a photograph of a completed company project.
Below-the-fold sections fade and slide into view as visitors scroll. Clicking a
top-menu section link replays that section's reveal, including on repeat visits.
About Us also replays the Client First content and its three cards.
The What We Do section uses blueprint-style icon panels and visible service
details for Construction, Design & Planning, and Project Coordination. Its content
also describes potential support for new homes, business spaces, renovations or
extensions, interior design, early design guidance and other agreed projects.
The Services menu links directly to this section. Project Starting Points serves
as the Plan your project destination, reusing the six project choices and
preparation checklists in an icon-led, hoverable list. It replaces the separate
Let's Start With Your Vision guide.
The Journey uses matching navigation and stage titles: Your Aspirations, Thoughtful
Design, Taking Shape and New Beginnings. Each detail panel shows its title once,
without a duplicate uppercase label.
The approved Journey uses the hover stage-panel layout, replacing both comparison
versions. The Our approach menu links directly to it. Hovering, focusing or tapping a stage
updates its illustration and complete details; the last preview stays selected
when the pointer leaves, allowing visitors to read the content.
The approved Journey uses the warmer, client-focused alternative content under
“Your story. Thoughtfully brought to life.” It retains the four titles, illustrations,
layout and interactions. The earlier content and comparison labels are no longer
displayed; Our approach links to the single approved Journey.
The website's VRIDHI wordmark uses lettering extracted from the supplied logo,
including its custom R, rather than a substitute font. A local transparent image
mask follows the header text colour in both themes; accessible text is retained.
The subtitle retains its existing font.
The approved readability contrast improvements are applied to the main website:
paragraph, checklist and small-note text, navigation links, section labels,
interface icons and card/control borders have stronger contrast in both themes.
Hover and selected icon treatments are retained. Fonts, sizes, weights, line spacing,
card proportions, section spacing, headings and logo lettering are unchanged.
There is no separate preview page, readability mode or typography preference.
The login heading and expanded application sidebar use the same logo-derived
lettering. The compact and mobile sidebars keep the existing logo-only layout.
Sections fully below the viewport reset when visitors scroll back up, so the effect plays
again on the next scroll down. Sections above the viewport remain revealed,
and a section containing keyboard focus is not reset.
Content is already loaded, not fetched on scroll. Keyboard focus also reveals
sections; reduced-motion mode, printing and browsers without IntersectionObserver
show content without the scroll effect.
Client-facing draft sections explain design priorities, scope clarity and
communication. A project discussion guide offers starting points for a new home,
business space, renovation or extension, interior design, design guidance, or
another project, with a preparation checklist for each. Selections
are not submitted or saved. A second, comparison layout follows the original guide:
project choices appear as an icon-led list beside the checklist, and the Contact
link points to the existing sample contact section. Both guide versions are local
only and do not send or save selections. Contact details, portfolio, testimonials and business
commitments require approval before publication; no enquiry delivery is wired.
Contact Us (`#contact`) describes meetings at an agreed location and project-site
visits by prior arrangement, with no walk-in office or published home address.
There are no fixed office hours; meeting times are agreed individually.
The contact introduction invites visitors to share their project plans, priorities
and questions; the separate idea callout has been removed as redundant.
A masked phone number and a reserved `.example` email address remain explicitly
labelled samples, not active contact links. Contact Us is details-only: there is no enquiry form, submission endpoint
or email-sending service. No enquiries are sent or stored by the website. Replace
sample details with approved business contacts before publication. Direct contact
through an existing phone or email account does not require website SMTP setup.

1. Start the configured database, backend, and frontend using the appropriate
   launcher, or ask support for the application URL.
2. Select **Login** on the website to open `/app` in a new tab (or open `/app`
   directly), then enter your username or work email, and password.
3. Select **Sign in**.
4. If you have only Users-page access, you can use Users without choosing a project.
   Project work requires an accessible project.

Wrong credentials receive a generic error. A correct password for an inactive
account produces: "Your account is disabled. Please contact your administrator
to reactivate it." Disabled/deleted accounts cannot obtain a valid application session.

There is no documented, implemented email-delivery recovery workflow here. Ask a
user manager with Reset Password permission to reset your password.

## Understand the screen

| Area | Purpose |
|---|---|
| Projects | Portfolio of projects accessible to your account |
| WORKSPACE picker | Switch projects; status appears beside each project |
| Left menu | Permitted modules for the current context |
| Breadcrumb / project context | Confirms which project you are working in |
| Day/Dark switch | Changes screen appearance; reports still print in day colors |
| Date and clock | Local browser date/time |
| Notes icon | Temporary personal notes available across modules |
| User badge | My Details: read-only account and permission summary |
| Sign out | Ends the session and clears that account's session notes |

The project picker closes after selection, outside click, or Escape. On phones,
the project picker is above the horizontally scrollable menu row. Swipe the menu
row to reach additional permitted modules; wide tables scroll inside their panels.

## Choose a project

Choose a card in Projects, or select a project from WORKSPACE. Confirm its name
before entering purchases, receipts, stock movements, or labor work. Switching
projects changes the data context and re-evaluates permissions.

Project lifecycle labels are Planning, Active, On Hold, Completed, and Cancelled.
They are business states, not permission levels. A financial action can also be
unavailable because of its record state, not merely because of access settings.

## Read versus write

- **Allow** lets you open a module; **Block** prevents access.
- **Download Report** is a separate read capability.
- **Write All** authorizes all applicable module actions.
- **Write Partial** authorizes only checked actions.
- Actions may be hidden or disabled when permission or record eligibility is missing.

See [permissions](04-users-and-permissions.md) before requesting broader access.

## Left menu preference

The left menu remembers whether it is collapsed or expanded in this browser,
including after a page refresh.
On desktop, navigation uses 40px rows with 13px text and 20px icons.
Collapsed navigation uses 44px rows with 25px icons. Icons change to an amber
color on hover or keyboard focus in both themes. The menu scrolls only
when needed on shorter windows, rather than reducing item sizes or hiding items.
Long selected project names wrap in the project picker rather than being clipped.

## Personal Notes

Open Notes, type reminders, and move between modules. Text, open/collapsed state,
and preferred panel width use account-specific browser session storage.

- Drag the panel's left edge to resize, or focus it and use arrow keys.
- Collapse does not erase the text; Clear asks for confirmation.
- Refresh in the same tab normally retains text.
- Successful sign-out clears the notes. Failed sign-out does not deliberately clear them.
- Closing the tab/session can remove notes; they are not shared or backed up in PostgreSQL.
- Notes do not appear in exported reports. Do not use them as permanent project records.

## A sensible first working session

1. Check My Details and confirm the assigned projects/permissions.
2. Select the correct project.
3. Review Overview, then the operational module you need.
4. Record a reference/comment when saving financial or stock activity.
5. Verify the resulting row and totals; use history where available.
6. Export a report if authorized, then sign out on a shared machine.
