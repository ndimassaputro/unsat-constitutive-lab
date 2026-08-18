# Peak-stress definition correction

## Issue

The first strength-analysis pass interpreted the Appendix-F peak-stress
column as total axial stress and calculated

`q_peak = sigma_a_peak - sigma_c_net`.

This double-subtracted the confining stress.

## Source-level verification

The Appendix-F stress-strain plot for ST-36 is explicitly labelled
`Deviatoric stress (kPa)` and reaches a peak of approximately 265 kPa.

Table F-1 reports 264.5 kPa for the corresponding ST-36 test
(matric suction = 152 kPa).

The table peak-stress value therefore corresponds directly to the
measured peak deviatoric stress used in the stress-strain figure.

## Correct definition

`q_peak_kPa = source peak-stress value`

No additional subtraction of net confining stress is applied.

## Consequence

All Phase-3 model fits and validation results obtained with the previous
derived q definition are superseded and must be recomputed.

The superseded files are retained for provenance rather than deleted.
