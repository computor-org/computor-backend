# Privacy Notice computor.at

Version 1.1, effective 1 October 2026

In this privacy notice, we inform you about how personal data are processed on
the learning platform computor.at and in the chat chat.computor.at. This
allows you to see at a glance which personal data we process, for what
purpose, and on which legal basis. We process your data exclusively on the
basis of the legal provisions for data protection and data security and, in
particular, the Austrian Data Protection Act (Datenschutzgesetz, “DSG”), the EU
General Data Protection Regulation (“GDPR”, in German “DSGVO”) and the Austrian
Telecommunications Act (“TKG 2021”). The German version is authoritative.

## Summary

- We process only what we need to provide your account, courses, workspace,
  automatic tests, chat and the Luna help you request.
- No advertising, no tracking, no analytics, no third-party services embedded
  in our web pages, no sale of data, no use of your data to train AI models.
- Only technically necessary cookies, so there is no cookie banner.
- Platform servers are in Germany (Hetzner); Luna inference runs at TU Graz in Austria.
- You sign up with a verified email address and a password. Public examples need no account.
- You can ask us to delete your account at any time: privacy@computor.at.

## 1. Scope

This notice applies to all processing on computor.at (including sign-in, the
browser workspaces and the Git server) and in the chat chat.computor.at. Both
services are run by the same controller.

## 2. Contact

The data controller for processing your personal data is Graz University of
Technology, Rechbauerstraße 12, 8010 Graz, Austria (hereinafter “TU Graz” or
“we”). The platform is run by the Institute of Theoretical Physics –
Computational Physics (ITPcp), Petersgasse 16, 8010 Graz.

The TU Graz data protection officer is x-tention Informationstechnologie GmbH,
Friedhofstraße 57, 4600 Wels, datenschutzbeauftragter@tugraz.at.

If you have any data protection concerns, please contact datenschutz@tugraz.at
or privacy@computor.at.

## 3. Legal basis

TU Graz runs computor.at to fulfil its statutory tasks in teaching, continuing
education and science communication (§§ 2 and 3 Universities Act 2002, “UG”).
Unless stated otherwise below, we therefore process your data on the basis of
the public interest under Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.
Processing is not based on your consent. Accepting the Terms of Use governs
your use of the platform; it is not consent under data protection law.

## 4. What we process and why

### 4.1 Sign-in and account

You create an account with your email address and password. Our sign-in
service (Keycloak) verifies your email and stores the password as a cryptographic
hash, never as readable text.

Categories of data: verified email address, username, name you provide, password
hash, internal user ID, time you accepted the Terms of Use, time of last sign-in.

Purpose: account creation, sign-in and account-related contact.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.

Your email address is required to create an account. Reading public examples
does not require an account.

### 4.2 Courses, submissions and tests

Categories of data: course enrolments, group membership, your code and other
submissions, Git repositories with their history (on our own Forgejo Git
server), automatic test results, points, feedback from teaching staff,
timestamps.

Purpose: running the courses, automatically testing your code, feedback and
support by teaching staff and tutors.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.

Test results and points are calculated automatically. They serve only your
learning; they produce no legal effects concerning you and do not similarly
significantly affect you. There is therefore no automated decision within the
meaning of Art. 22 GDPR. If a university course uses results from computor.at
for an assessment, the responsible teacher decides, not the platform.

### 4.3 Browser workspaces

Categories of data: files in your workspace (browser version of Visual Studio
Code, based on Coder), processes running in it, start and stop times.

Purpose: providing a programming environment that needs no local installation.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.

Workspaces are stopped automatically after one hour without activity. Files in
your home directory are kept as long as your account exists. The operations
team accesses the content of your workspace only to fix a problem at your
request or where there is a specific suspicion of abuse.

### 4.4 Chat (chat.computor.at)

The chat is a separate service (Zulip) with its own account. You can sign in
with GitHub or with email address and password; we store passwords only as a
cryptographic hash.

Categories of data: name, email address, profile details, messages,
reactions, uploaded files, timestamps, notification settings.

Purpose: communication between participants, teaching staff and tutors; email
notifications if you have enabled them.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.

### 4.5 Creation of log data (access data)

In order to be able to provide our online services, log data that are
technically necessary are stored each time our online offer is accessed. The
log data enable us to detect, limit and eliminate system malfunctions, system
errors, malfunctions that can restrict the availability of the online services
as well as unauthorised access to our systems. The log data are not linked to
other personal data unless this is necessary to investigate a specific
security incident.

Categories of data: date and time of the request, name and URL of the
retrieved resource, amount of data, response of the server (e.g. HTTP status
code), identification data for the browser and operating system used, website
from which the access was made, IP address.

Legal basis: we store the log data for a limited period of time to fulfil our
legitimate interest in secure and reliable operation according to
Art. 6(1)(f) GDPR.

Storage period: 14 days.

### 4.6 Security and abuse monitoring

Anyone can run programs in the workspaces. To detect abuse (e.g.
cryptocurrency mining or attacks on third parties), we automatically record
aggregate figures per workspace: CPU usage and number of network connections.
These values are evaluated in memory and not stored permanently. We do not see
the content you transmit.

If a workspace exceeds set thresholds, an alert attributed to your account
(username, workspace, measured values, time) is created in an internal
channel that only the operations team can access. A human decides on any
measures; to protect against acute danger, a workspace may also be stopped
automatically.

Legal basis: Art. 6(1)(f) GDPR (legitimate interest in protecting the
platform, its users and third parties; see also Art. 32 GDPR).

Storage period of alerts: 90 days; in the case of a specific incident, until
it is resolved.

### 4.7 Enquiries and reports

If you email us or report content, we process your message and contact details
to handle it.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG; for reports
of illegal content, Art. 6(1)(c) GDPR in conjunction with Articles 16 and 17 of
Regulation (EU) 2022/2065 (Digital Services Act, “DSA”), where applicable.

Storage period: until the matter is closed, then at most three years for
traceability and the defence of legal claims.

### 4.8 Luna learning assistance

When you ask Luna, we process your question, the text you choose to submit,
the assignment description visible to you and the generated answer. Luna gives
learning help; it does not run your code or decide grades. Inference takes place
on TU Graz machines in Austria, without an external AI provider or model training.

Legal basis: Art. 6(1)(e) GDPR in conjunction with §§ 2 and 3 UG.

The request is held temporarily on computor.at for at most 15 minutes; after
completion it is removed, and only you can retrieve the answer for 24 hours.
The inference worker keeps no prompt or answer files or content logs. The model
uses bounded memory and local disk caches to reuse computations. Cache entries
are replaced when capacity is needed or the cache is cleared; they have no fixed
time-based expiry. These caches are private to the inference service and are
not made available to learners. We retain numeric size, status and timing
telemetry without question, submitted-text or answer contents.

## 5. Who sees your data

- **Teaching staff and tutors of your course** see your name, username,
  submissions, test results, points and progress.
- **Other participants** see your name and your messages in the chat channels
  where you post. Your submissions are not visible to other participants
  unless a course provides for group work.
- **The operations team** (a few administrators at ITPcp) has technical access
  to the servers and uses it only for operation, troubleshooting and abuse
  prevention.
- Your submissions and workspaces are **not public**.

## 6. Recipients and processors

We run all services of the platform ourselves (sign-in with Keycloak, Forgejo
Git server, database, file storage, test system, workspaces with Coder, chat
with Zulip). Fonts are served from our own servers. We do not embed content delivery networks, analytics, advertising or external AI services. Luna is operated by TU Graz.

| Recipient | Role | Location | Basis |
|---|---|---|---|
| Hetzner Online GmbH, Industriestraße 25, 91710 Gunzenhausen, Germany | processor: servers, storage, backups | data centres in Nuremberg and Falkenstein, Germany | data processing agreement under Art. 28 GDPR |
| Authorities and courts | only where required by law or to report serious criminal offences (Art. 18 DSA) | Austria or EU | Art. 6(1)(c) GDPR |

**Optional GitHub Codespaces:** If you choose this way of working, GitHub
provides the development environment under its own terms and privacy notice.
It is separate from computor.at; you decide which files to put there. Desktop
VS Code and the anonymous read-only examples remain available as alternatives.

Emails from the platform (e.g. chat notifications) are sent via the TU Graz
mail server. Beyond this, your data are not transferred to third countries. We
do not sell your data and do not use them for advertising or to train AI
models.

## 7. Cookies and similar technologies

Here, “cookie(s)” also covers technologies that are similar to cookies in
terms of functionality, such as the browser's local storage.

We use only technically necessary cookies (functional cookies) according to
the exemption clause in § 165(3) TKG 2021. The user's consent is not required;
therefore there is no cookie banner. We do not use analytics or advertising
cookies. The cookies relate only to computor.at or chat.computor.at; no data
are transmitted to third parties.

| Name | Purpose | Duration | Provider |
|---|---|---|---|
| `KEYCLOAK_SESSION`, `KEYCLOAK_IDENTITY`, `AUTH_SESSION_ID`, `KC_RESTART` and similar | sign-in session at the sign-in service | session or until sign-in expires | TU Graz (Keycloak) |
| `ct_access_token` | platform access token | 1 hour | TU Graz |
| `ct_refresh_token` | renewing the sign-in | 7 days | TU Graz |
| `coder_session_token` and similar | workspace session | until the session expires | TU Graz (Coder) |
| `sessionid`, `csrftoken` (also with prefix `__Host-`) | chat session and protection against cross-site request forgery | until sign-out or expiry | TU Graz (Zulip) |
| `computor-theme` (local storage) | your light/dark theme preference | until you delete it | TU Graz |

You can control cookies and their storage period in your browser settings.
Without these cookies, however, signing in is not possible.

## 8. Storage periods

| Data | Period |
|---|---|
| Account, course enrolments, submissions, Git repositories, test results | until your account is deleted |
| Workspace files (home directory) | until your account is deleted |
| Luna requests | at most 15 minutes; removed on completion |
| Luna answers | 24 hours, visible only to the author |
| Luna inference caches | bounded capacity; replacement on capacity pressure or clearing |
| Chat account and messages | until you delete messages or your chat account, or ask us to delete it |
| Web server access logs (log data) | 14 days |
| Security alerts attributed to an account | 90 days |
| Enquiries and reports | until closed, then at most three years |
| Backups (server snapshots) | daily backups are kept for 7 days; backups made before maintenance for at most 30 days |

**Inactive accounts:** we delete accounts, together with their data, that have
not been signed in to for 24 months. We announce the deletion by email at
least 30 days in advance; signing in during this period keeps the account.

**Deletion and backups:** deleted data disappear from all backups at the
latest 30 days after deletion. In the case of a specific security incident, we
keep the data needed until it has been resolved.

## 9. Rights of data subjects

You have the rights to access, rectification and erasure of your data, as well
as the right to restriction and the right to data portability of the data you
have provided. If the processing is based on the legal basis of legitimate or
public interest, you can lodge a justified objection to the processing
(Art. 21 GDPR).

In order to process your request and to ensure that personal data are not
disclosed to unauthorised third parties, we must identify you clearly. Please
therefore write to privacy@computor.at or datenschutz@tugraz.at from the email
address linked to your account. We usually reply within one month
(Art. 12(3) GDPR).

There is also a right to lodge a complaint with the Austrian Data Protection
Authority (Österreichische Datenschutzbehörde), Barichgasse 40–42, 1030 Vienna,
Austria, dsb@dsb.gv.at, https://www.dsb.gv.at.

## 10. Minimum age

You may use computor.at and chat.computor.at from the age of 14. Processing of
your data is not based on consent (see section 3), so you do not need your
parents' consent for it. Persons under 14 may not create an account. If we
learn that an account belongs to a person under 14, we delete it.

## 11. Security

All connections are encrypted (TLS). User code runs in separate containers
with resource limits. Server access is restricted to the operations team.
Please report security vulnerabilities to security@computor.at or
confidentially via https://github.com/computor-org/feedback/security/advisories/new.

## 12. Changes to this notice

If our processing changes, we update this notice. We inform registered users
of material changes by email or at their next sign-in. The current version is
available at https://computor.at/privacy; previous versions are also
available there.
