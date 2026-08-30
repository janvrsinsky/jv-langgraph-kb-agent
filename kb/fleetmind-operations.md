# FleetMind Operations Runbook, Acme Robotics

## What FleetMind is responsible for

FleetMind assigns tasks to mixed fleets of AcmeArms and AcmeCarts, holds the
site map, and arbitrates traffic between carts. It does not drive the robots:
each unit runs its own motion control and will stop on its own if it loses the
server. A FleetMind outage therefore halts new work but never causes motion.

## Sizing a site

One FleetMind server handles up to 120 carts per site. Beyond that the site is
split into zones with one server each and a read-only federation view for the
site manager. PostgreSQL 15 or newer is a hard dependency; the task planner
uses range types that older versions do not have.

## Restarting the server

A rolling restart is safe at any time: carts finish the task in hand and queue
the next one. A cold restart clears the queue, so it is done only during a
planned stop, and the queue is exported first with `fleetctl queue dump`.

## When carts stop moving

Check three things in order: the site map lock (a stale lock blocks every
assignment), the PostgreSQL connection pool, and the wireless bridge on the
affected aisle. In practice the aisle bridge is the cause about half the time,
and it presents as one zone frozen while the rest of the site runs normally.

## Traffic deadlocks

Two carts facing each other in a single-width aisle resolve by seniority: the
one with the older task backs out. If both back out repeatedly, the aisle is
mapped wrongly as bidirectional and the map needs correcting, which is a
change to the site map and not something to fix by restarting.

## Backups and recovery

The site database is backed up hourly with a 30-day retention, and a restore
is rehearsed quarterly. An untested backup is treated as no backup, so the
rehearsal is a real restore into a staging site, not a file listing.

## Upgrades

FleetMind upgrades one minor version at a time, never skipping, and always with
the fleet stopped. The upgrade migrates the site map schema and there is no
supported downgrade; the rollback path is a database restore.

## FleetMind Copilot

The natural-language task planner is in private beta with three customers. It
proposes task assignments in plain language and every proposal still goes
through the same validation as a manually entered task, so it cannot schedule
something the ordinary planner would reject.
