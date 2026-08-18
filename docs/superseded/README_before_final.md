# UnsatConstitutiveLab

## Laboratory-Calibrated Constitutive Modelling of Unsaturated Soil under Triaxial Stress Paths

**Research question**

> How well can laboratory-calibrated constitutive descriptions reproduce and
> predict the suction-dependent strength and stress-strain response of
> unsaturated residual soil across different stress states?

UnsatConstitutiveLab is an independent computational geomechanics study focused
on the calibration, verification, and validation of constitutive descriptions
against real laboratory triaxial data.

The project is designed around three principles:

1. use real laboratory observations rather than synthetic truth;
2. distinguish parameter calibration from holdout prediction;
3. increase constitutive complexity only when supported by the available data.

## Planned modelling hierarchy

### Level 1 — Saturated reference

Establish the conventional effective-stress strength envelope and reference
mechanical parameters.

### Level 2 — Suction-dependent shear strength

Calibrate an unsaturated strength description in which matric suction
contributes to shear resistance.

### Level 3 — Nonlinear constitutive response

Implement and test a single-element nonlinear elastoplastic constitutive model
for the available triaxial stress paths.

The final model level will be selected only after assessment of parameter
identifiability and experimental-data coverage.

## Verification philosophy

The project separates:

- implementation verification,
- calibration fit,
- holdout validation,
- parameter sensitivity,
- identifiability,
- and model-form limitations.

A visually good calibration curve alone is not considered validation.

## Scope

This project does not claim:

- field-scale slope prediction,
- rainfall infiltration simulation,
- finite-element boundary-value modelling,
- or a complete general-purpose unsaturated-soil constitutive law.

The objective is laboratory-informed constitutive modelling at element-test
level as preparation for coupled hydro-mechanical geomechanics.
