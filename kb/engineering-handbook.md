# Engineering Handbook, Acme Robotics

## How work reaches production

Every change lands through a pull request against `main`. Two approvals are
required for anything touching the controller firmware or FleetMind's task
planner; one approval is enough elsewhere. Trunk is always deployable, and a
release is a tag on `main`, never a long-lived branch.

## Code review expectations

Reviewers answer within one working day. A review that only says "looks good"
on a change over 400 lines is treated as unreviewed. Reviewers are asked to
state what they actually checked, so the author knows which risks were covered
and which were not.

## Deployment windows

FleetMind server releases go out Tuesday and Thursday between 08:00 and 11:00
Prague time, deliberately outside the customer shift change at 14:00. Robot
firmware is different: it is staged to one site for a full production week
before any fleet-wide rollout.

## Rollback

Every deploy carries a rollback command in its release notes, and the person
who pressed deploy owns the rollback decision for the next four hours. A
rollback needs no approval and no incident review; deploying again after one
does.

## On-call

Engineering on-call rotates weekly, handover Monday 10:00. The rotation covers
FleetMind and the fleet dashboard only; robot firmware issues escalate to the
controls team, who are not on a pager rotation and answer during Prague office
hours.

## Testing floor

A change is not mergeable without a test that would have failed before it. The
CI suite runs on every push and the build fails if coverage of the task planner
drops below 80 percent, which is the only coverage number anyone enforces.

## Technical decisions

Anything that changes an interface between two teams gets a one-page decision
record in the wiki before implementation, not after. The record names the
option that was rejected and why, because that is the part people forget.
