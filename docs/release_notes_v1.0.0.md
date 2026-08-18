# UnsatConstitutiveLab v1.0.0

Initial public research release of **UnsatConstitutiveLab**.

## Scope

This repository presents a reproducible secondary computational analysis of
published unsaturated triaxial tests on natural residual soils.

The project combines:

- source-anchored reconstruction of published stress–strain curves;
- suction-dependent strength modelling;
- laboratory-calibrated constitutive parameterization;
- leave-one-tube-out predictive validation;
- tube-clustered bootstrap uncertainty analysis;
- paired multistage stress-path analysis;
- explicit falsification and sensitivity tests; and
- model-free confirmation of the principal mobilization result.

## Dataset coverage

The audited source archive contains:

- 46 unsaturated triaxial specimens/tests;
- 20 single-stage specimens;
- 26 multistage specimens;
- 86 stage-level strength observations; and
- 36 unique source tubes.

The final stress–strain reconstruction contains:

- 45 usable figures;
- 84 reconstructed stage curves; and
- 45 represented specimens.

## Constitutive representation

Normalized pre-peak response is represented using

\[
y = \frac{x(1+\lambda)}{1+\lambda x},
\]

where the fitted parameter \(\lambda\) provides a compact description of
mobilization curvature.

Across 84 reconstructed stages:

- median pre-peak normalized fitting error ≈ 3.2%;
- 90th-percentile fitting error ≈ 5.5%.

The relation is used as a compact constitutive descriptor rather than as a
proposed universal constitutive law.

## Primary result

For 25 paired Stage-1/Stage-2 specimens from 18 independent source tubes,
Stage 2 exhibits systematically earlier normalized pre-peak stress
mobilization than Stage 1 under the investigated multistage protocol.

At half normalized peak strain:

\[
\Delta y_{50} \approx +0.171
\]

with a 95% tube-cluster bootstrap interval of approximately

\[
[+0.132,\,+0.210].
\]

The primary scientific inference is based on direct model-free mobilization
descriptors rather than on the fitted constitutive parameter alone.

## Robustness

The result persists across alternative stage-start stress definitions and
within the major MH and ML soil subsets.

The available data do not uniquely identify the physical mechanism. The
observed shift should therefore not automatically be interpreted as intrinsic
material hardening.

## Research integrity

This is a secondary analysis of third-party laboratory data.

Primary source:

C.-T. Tang, R. H. Borden, and M. A. Gabr,
*Model Applicability for Prediction of Residual Soil Apparent Cohesion*,
Transportation Geotechnics 19 (2019), 44–53.

Dataset DOI: `10.17632/p9tmzckdpt.1`

Original code and documentation in this repository are released under the MIT
License. See `THIRD_PARTY_NOTICES.md` for the source-data attribution boundary.
