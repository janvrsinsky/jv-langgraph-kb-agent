# AcmeCart AMR Service Manual, Acme Robotics

## Specification recap

Autonomous mobile robot for intralogistics. Payload 250 kg, runtime 9 hours,
swappable battery, navigation by LiDAR combined with visual SLAM. Coordinated
by FleetMind, up to 120 carts per site.

## Battery handling

The pack is hot-swappable and takes about 90 seconds to change. Charge between
20 and 90 percent for daily use; a full charge to 100 is only for a capacity
test. A pack that has fallen below 10 percent three times in a week is flagged
for replacement, because that pattern predicts a capacity cliff.

## Navigation problems

A cart that hesitates at the same spot every run is usually seeing a reflective
surface, not a mapping error. Shrink wrap, polished floor near a loading door
and mirrored panels are the three usual culprits. The fix is a no-go polygon in
the site map or a matte surface, not a LiDAR replacement.

## Localization loss

If a cart reports lost localization after a layout change, the map is stale.
Re-scan the affected aisle rather than the whole site; a partial re-scan merges
cleanly and takes about 20 minutes per aisle.

## Common error codes

C-050 is an obstacle timeout: something has been in the path longer than the
configured wait, and the cart is behaving correctly by stopping. C-118 is a
drive current spike and usually means a wheel is fouled by strapping or film.
C-203 is a battery communication fault and is the one code that requires the
pack be taken out of service until it is checked.

## Wheels and drivetrain

Drive wheels are inspected every 500 operating hours and replaced at 3 mm
remaining tread. Castors are cleaned at the same interval; wound-in packaging
film is the single most common cause of unplanned cart downtime.

## Cleaning the sensors

The LiDAR window and the two navigation cameras are wiped daily in dusty sites
and weekly elsewhere, with a dry microfibre cloth and no solvent. Solvent
crazes the window and the damage looks exactly like sensor failure.

## Safety

The cart stops for anything in its protective field and resumes on its own once
the path clears. Riding on a cart, loading beyond 250 kg, or defeating the
field with tape are each grounds for taking the unit out of service.
