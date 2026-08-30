# Security Policy, Acme Robotics

## Passwords and sign-in

Acme does not use passwords for internal systems. Everything sits behind Okta
single sign-on with hardware keys or platform passkeys as the second factor.
If you cannot sign in, the fix is an Okta account reset by IT through the
#it-requests channel, not a password change, because there is no password to
change. SMS codes were retired in 2025 and will not be re-enabled.

## Lost or stolen devices

Report within one hour to security@acme-robotics.example and the
#security-incidents channel. IT wipes the device remotely and revokes its Okta
sessions. A replacement laptop is issued within two working days from the
Prague office stock.

## Phishing

Anything asking for a code, a signature, or an urgent payment is treated as
phishing until proven otherwise. Forward it as an attachment and do not click
to check. Reporting something that turns out to be legitimate is explicitly
not a mistake and is never counted against anyone.

## Customer data on laptops

Customer telemetry may be pulled to a laptop only for an active support case
and must be deleted when the case closes. Full fleet exports never leave the
data platform; if an analysis needs the whole set, it runs where the data is.

## Robot network segmentation

Robot fleets sit on a separate VLAN with no route to the office network. The
only path in is the WireGuard profile `acme-wg`, and it is issued per person,
never shared between engineers. A shared profile is a reportable incident.

## Vulnerability handling

Anything reachable from a customer site is patched within 7 days for critical
findings, 30 days for high. The clock starts when the finding is filed, not
when it is triaged, which is the part vendors usually argue about.

## Physical access

Badges open the Karlín office between 06:00 and 22:00. Outside those hours
entry needs a second person present, and the robot lab is badge-plus-PIN at
all times because there is powered machinery inside.
