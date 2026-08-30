# AcmeArm 3000 Service Manual, Acme Robotics

## Specification recap

Six-axis industrial arm, payload 12 kg, reach 1.4 m, maximum joint torque
310 Nm, repeatability plus or minus 0.02 mm. Controller is AcmeOS 4 with a
Python SDK. Rated for continuous duty at 40 degrees Celsius ambient.

## Routine maintenance

Grease the joint 2 and joint 3 gearboxes every 2000 operating hours. Belt
tension on joints 4 to 6 is checked at the same interval. Cycle counters live
in the controller and are read with `acmectl hours`, not estimated from the
production calendar.

## Accuracy drift

If placement accuracy degrades without an alarm, the usual cause is a
temperature-related zero offset rather than mechanical wear. Run the warm-up
program for 20 minutes and re-measure before opening anything. Wear shows up
as repeatability loss in both directions; a thermal offset shows up as a
consistent shift in one.

## Common error codes

E-104 is a joint overtorque trip and means the arm hit something, not that the
motor failed. E-220 is an encoder communication fault and is a cable or
connector problem in nine cases out of ten. E-311 is a brake release failure
and is the one code that must never be cleared without a physical inspection,
because the brake holds the arm's own weight.

## Calibration

Full six-axis calibration needs the calibration fixture and takes about three
hours. It is required after any gearbox replacement, after a collision that
tripped E-104 above 80 percent of rated torque, and yearly regardless.

## Safety envelope

The arm ships with a configured safe zone; changing it is a commissioning task
with a second person signing off. A collaborative mode exists but is limited to
a payload of 3 kg and a reduced speed, and it is not a substitute for a fence
at full payload.

## Spare parts

Joint gearboxes, encoders, brake assemblies and the wrist cable harness are
kept in the Prague warehouse with next-day dispatch across Europe. Everything
else is build-to-order at roughly six weeks.
