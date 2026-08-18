# Research Plan

## Scientific objective

Quantify how matric suction modifies the mechanical response of unsaturated
residual soil and evaluate whether increasingly sophisticated constitutive
descriptions provide genuinely improved predictive performance.

## Phase 0 — provenance and reproducibility

- establish reproducible Python environment;
- archive source and licence information;
- preserve raw experimental data unchanged.

## Phase 1 — laboratory-data reconstruction

For every usable triaxial test, extract or reconstruct:

- axial strain;
- deviatoric stress q;
- confining/net stress;
- matric suction;
- pore/air pressure where available;
- soil group;
- specimen condition;
- failure or peak-strength state.

Perform dimensional and physical consistency checks.

## Phase 2 — experimental interpretation

Construct:

- q versus axial strain;
- peak strength versus suction;
- stress-state tables;
- apparent cohesion versus suction;
- available effective-stress paths.

No constitutive calibration is allowed before these plots pass QC.

## Phase 3 — baseline strength models

Fit a hierarchy beginning with:

1. saturated Mohr-Coulomb reference;
2. Fredlund-type suction-dependent shear strength.

Compare calibration and holdout prediction.

## Phase 4 — nonlinear constitutive modelling

Implement a single-element nonlinear elastoplastic constitutive formulation.

Candidate formulation will be selected after Phase 2 according to:

- available state variables;
- calibration information content;
- parameter identifiability;
- relevance to unsaturated soil behaviour.

A more complicated model will not be used solely because it is more advanced.

## Phase 5 — calibration and validation

Use explicit calibration/validation separation.

Evaluate:

- RMSE;
- normalized RMSE;
- peak-strength error;
- stress-path error where available;
- parameter sensitivity;
- identifiability / parameter correlation.

## Phase 6 — model-form assessment

Ask whether additional model complexity improves prediction outside the
calibration data.

Document failure modes and unsupported mechanisms.

## Final scientific question

Does laboratory-calibrated suction-dependent constitutive modelling provide
predictive information beyond a conventional saturated strength description,
and which aspects of the observed response remain unresolved?
