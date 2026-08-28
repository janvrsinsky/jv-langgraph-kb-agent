# IT Handbook, Acme Robotics

## Accounts and access

All access is managed through Okta single sign-on. New tools are requested
via the #it-requests Slack channel. Admin rights on laptops are not granted
by default; temporary elevation is available through the Privileges app
for 30-minute windows.

## VPN

The corporate VPN is WireGuard-based, profile name `acme-wg`. It is required
for access to the robot fleet dashboard and the internal PyPI mirror.
Config profiles are distributed through Okta, never by email.

## Security incidents

Suspected phishing or a lost device must be reported within 1 hour to
security@acme-robotics.example and the #security-incidents channel.
The on-call security engineer rotates weekly; the schedule lives in PagerDuty.

## Hardware refresh

Laptops are refreshed every 36 months. Engineers get a choice between a
MacBook Pro 14" and a ThinkPad X1 running Ubuntu LTS.
