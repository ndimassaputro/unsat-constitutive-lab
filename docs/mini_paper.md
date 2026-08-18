# UnsatConstitutiveLab

## Laboratory-Calibrated Constitutive Modelling of Unsaturated Soil under Triaxial Stress Paths

### Working research question

**How well can laboratory-calibrated constitutive descriptions reproduce
and predict the suction-dependent strength and stress-strain response of
unsaturated residual soil across different stress states, and what
additional information is carried by multistage loading history?**

---

# 1. Scope

This project performs a secondary computational analysis of published
unsaturated triaxial test data for natural residual soils.

The work combines:

1. source-anchored reconstruction of laboratory stress-strain curves;
2. suction-dependent shear-strength modelling;
3. specimen-independent predictive validation;
4. compact constitutive representation of pre-peak stress mobilization;
5. paired within-specimen analysis of multistage response; and
6. bootstrap-based robustness and uncertainty assessment.

The project does **not** propose a universal unsaturated constitutive law.

It focuses instead on extracting defensible constitutive information from
an existing experimental archive while preserving explicit calibration,
validation, provenance, and uncertainty boundaries.

---

# 2. Experimental data source

The primary source is:

C.-T. Tang, R. H. Borden, and M. A. Gabr,

**"Model Applicability for Prediction of Residual Soil Apparent Cohesion"**

Transportation Geotechnics, 19 (2019), 44-53.

Dataset DOI:

**10.17632/p9tmzckdpt.1**

The archived PDF contains tabulated test conditions, peak responses,
soil-state information, soil-water retention information, and full
stress-strain plots.

The broader Appendix F inventory contains:

- 46 unsaturated triaxial specimens/tests;
- 20 single-stage specimens;
- 26 multistage specimens.

The stage-level strength database contains:

- 86 stage observations;
- 46 specimens;
- 36 unique source tubes.

The published paper itself analyzes a smaller subset and should not be
described as having reported the full-curve findings developed in this
project.

---

# 3. Data reconstruction

## 3.1 Stress definition

The source stress-strain plots explicitly report:

**Deviatoric stress, \(q\), in kPa.**

Therefore, the source peak stress column is interpreted directly as the
measured peak deviatoric stress:

\[
q_p = q_{\text{source peak}}.
\]

No additional subtraction of net confining stress is applied.

This interpretation was independently checked against the ST-36 source
curve:

- source peak: 264.5 kPa;
- digitized peak: approximately 266 kPa;
- peak discrepancy: approximately 0.6%.

---

## 3.2 Full-curve digitization

A source-anchored digitization workflow was developed for the Appendix F
stress-strain plots.

Final reconstruction coverage:

- 46 figures attempted;
- 45 figures retained as usable;
- 84 stage curves reconstructed;
- 45 unique specimens represented.

Digitized peak-stress agreement was strong:

- median absolute peak discrepancy: approximately 0.43%;
- 90th-percentile absolute discrepancy: approximately 2.2%.

Strain-axis confidence was tracked separately because some plots allowed
direct tick calibration whereas others required a template-based axis
mapping.

Absolute strain-derived quantities must therefore be interpreted more
cautiously than scale-invariant normalized shape quantities.

---

# 4. Strength modelling

Unsaturated shear strength was first represented using a conventional
Fredlund-type expression:

\[
\tau_f
=
c'
+
(\sigma-u_a)\tan\phi'
+
(u_a-u_w)\tan\phi^b.
\]

Here:

- \(c'\) is a fitted cohesion-related term;
- \(\phi'\) is a fitted friction-related parameter;
- \(u_a-u_w\) is matric suction;
- \(\phi^b\) describes fitted suction-related strength contribution.

These pooled fitted quantities are treated as **equivalent fitted strength
parameters**, not as universally transferable fundamental material
constants.

Leave-one-tube-out cross-validation showed that including suction improved
peak-strength prediction relative to a net-stress-only Mohr-Coulomb
baseline, although the magnitude differed between soil classes.

Additional hydraulic-state variables were subsequently evaluated using
tube-wise predictive validation rather than in-sample goodness of fit.

---

# 5. Constitutive representation of pre-peak response

## 5.1 Normalized mobilization

For each stage, the pre-peak response is represented using:

\[
x
=
\frac{\varepsilon_a}
     {\varepsilon_{a,p}},
\]

and

\[
y
=
\frac{q-q_0}
     {q_p-q_0}.
\]

Where:

- \(\varepsilon_a\) is axial strain;
- \(\varepsilon_{a,p}\) is stage-specific axial strain at peak stress;
- \(q\) is deviatoric stress;
- \(q_p\) is stage-specific peak deviatoric stress;
- \(q_0\) is the stage-start deviator-stress baseline.

Thus:

\[
x=0,\ y=0
\]

represents the normalized stage start, and

\[
x=1,\ y=1
\]

represents the stage-specific peak.

---

## 5.2 Compact hyperbolic descriptor

A one-parameter normalized mobilization representation was used:

\[
y
=
\frac{x(1+\lambda)}
     {1+\lambda x}.
\]

The parameter \(\lambda\) controls the curvature of pre-peak strength
mobilization.

In simple terms:

- lower \(\lambda\): strength mobilizes more gradually;
- higher \(\lambda\): a greater fraction of peak strength is mobilized
  earlier in normalized strain.

The 84 reconstructed stages were fitted successfully.

Median normalized pre-peak fitting error was approximately:

\[
3.2\%.
\]

The 90th percentile was approximately:

\[
5.5\%.
\]

The hyperbolic equation is used as a compact constitutive representation,
not as a claim of a new constitutive law.

---

# 6. Specimen-independent constitutive prediction

Predictive models were evaluated using **leave-one-tube-out validation**.

This is stricter than random train-test splitting because all observations
originating from the held-out source tube remain unseen during calibration.

The predictive hierarchy examined combinations of:

- net confining stress;
- matric suction;
- degree of saturation;
- dry density;
- suction-saturation interaction;
- test-family and stage-history information.

Hydraulic-state models improved whole pre-peak curve prediction relative
to simpler mechanical descriptions.

However, decomposition of predictive errors showed that hydraulic-state
information alone did not provide strong, definitive evidence for a large
independent change in normalized curve shape.

A stronger signal emerged when multistage loading structure was examined
directly.

---

# 7. Primary multistage finding

## 7.1 Paired comparison

The primary analysis compares **Stage 1 and Stage 2 within the same
multistage specimen**.

This paired design reduces confounding from specimen-to-specimen
variability.

The final sample contains:

- 25 paired Stage-1/Stage-2 specimens;
- 18 independent source tubes.

Statistical uncertainty is evaluated by resampling at the tube level.

---

## 7.2 Direct model-free mobilization descriptors

The primary scientific inference does not depend on the hyperbolic
parameter \(\lambda\).

Direct normalized mobilization is evaluated at:

\[
x=0.25,\quad
x=0.50,\quad
x=0.75,
\]

giving:

\[
y_{25},\quad
y_{50},\quad
y_{75}.
\]

A mean mobilization descriptor is also calculated over:

\[
0.10\leq x\leq0.90.
\]

For the primary \(q_0\) definition, Stage 2 minus Stage 1 produced:

\[
\Delta y_{25}
=
+0.162,
\]

with 95% tube-cluster bootstrap interval:

\[
[+0.115,\,+0.209].
\]

At half normalized peak strain:

\[
\boxed{
\Delta y_{50}
=
+0.171
}
\]

with:

\[
\boxed{
95\%\ \mathrm{CI}
=
[+0.132,\,+0.210]
}
\]

and 92% of paired specimens showed a positive Stage-2 shift.

At:

\[
x=0.75,
\]

the difference remained positive:

\[
\Delta y_{75}
=
+0.085,
\]

with:

\[
95\%\ \mathrm{CI}
=
[+0.065,\,+0.105].
\]

For the complete normalized pre-peak interval:

\[
\boxed{
\Delta \bar y_{10-90}
=
+0.131
}
\]

with:

\[
\boxed{
95\%\ \mathrm{CI}
=
[+0.100,\,+0.161].
}
\]

---

# 8. Interpretation

The result indicates that, under the investigated multistage protocol,
the second shearing stage mobilizes a larger fraction of its own
stage-specific peak deviator-stress increment at the same normalized
strain than the first stage.

In simple terms:

> **The Stage-2 curve reaches a larger fraction of its eventual peak
> strength earlier in its normalized pre-peak deformation path.**

This is described as:

**earlier normalized pre-peak stress mobilization.**

The observation should not automatically be interpreted as intrinsic
material hardening.

Potential contributing mechanisms may include:

- prior shearing;
- stress-path evolution;
- loading/unloading or termination procedure;
- fabric evolution;
- accumulated plastic deformation; or
- other protocol-dependent effects.

The present dataset does not independently isolate these mechanisms.

---

# 9. Robustness

## 9.1 Stage-start stress sensitivity

The primary analysis estimates \(q_0\) from the first 5% of
stage-specific peak strain.

Sensitivity analysis repeated the calculation using:

- 2%;
- 5%;
- 10%;
- 15%

of \(\varepsilon_{a,p}\).

The Stage-1 to Stage-2 shift remained positive for all mobilization
descriptors at every tested baseline definition.

For example:

\[
\Delta y_{50}
\]

remained approximately:

\[
+0.166
\text{ to }
+0.184
\]

across the full \(q_0\)-window sensitivity range.

All corresponding 95% tube-cluster bootstrap intervals remained above
zero.

---

## 9.2 Soil-class stratification

The Stage-1 to Stage-2 shift was independently present in both major soil
subsets.

For MH soils:

\[
\Delta\bar y_{10-90}
\approx
+0.160,
\]

with 95% interval approximately:

\[
[+0.117,\,+0.196].
\]

For ML soils:

\[
\Delta\bar y_{10-90}
\approx
+0.105,
\]

with approximately:

\[
[+0.071,\,+0.141].
\]

The finding is therefore not carried entirely by one of these two soil
classes.

SC is not assigned the same inference because the number of independent
SC tubes is insufficient for a comparable stratified analysis.

---

# 10. Constitutive interpretation through lambda

The incremental hyperbolic parameter \(\lambda\) provides a compact
representation of the directly observed mobilization shape.

Across all 84 stages:

\[
\rho
\approx
0.996
\]

between \(\lambda\) and the model-free mean mobilization descriptor
\(\bar y_{10-90}\).

The relationship remains approximately:

\[
\rho
\approx
0.996
\]

when restricted to multistage observations.

Therefore, variation in \(\lambda\) closely follows a shape change that is
already directly visible in the reconstructed stress-strain data.

For tube-paired Stage 1 to Stage 2 comparisons:

\[
\Delta\lambda
\approx
+2.62,
\]

with a 95% tube-cluster bootstrap interval approximately:

\[
[+1.66,\,+3.73].
\]

The probability of a positive tube-level mean shift was approximately:

\[
P(\Delta\lambda>0)=1.000
\]

under the bootstrap analysis.

The scientific claim nevertheless remains anchored to the direct,
model-free mobilization descriptors rather than to \(\lambda\) alone.

---

# 11. Important falsification tests

Several alternative explanations were explicitly investigated.

## 11.1 Single-stage versus multistage family effect

Stage-1 multistage tests already differed from single-stage tests.

Therefore:

**single-stage versus multistage differences cannot be interpreted
entirely as accumulated loading history.**

There is a protocol/family offset before repeated shearing is considered.

---

## 11.2 Within-specimen history test

Within multistage specimens, later stages nevertheless showed a systematic
increase in mobilization curvature relative to Stage 1.

This survived within-specimen pairing and tube-level uncertainty analysis.

---

## 11.3 Stage-start stress correction

The multistage signal remained after response was reformulated using:

\[
\Delta q=q-q_0
\]

and:

\[
\Delta q_p=q_p-q_0.
\]

Therefore, non-zero stage-start deviator stress does not explain the
observed normalized mobilization shift.

---

## 11.4 Uniform strain-axis scaling

Because:

\[
x=
\frac{\varepsilon_a}
     {\varepsilon_{a,p}},
\]

uniform rescaling of the strain axis cancels exactly.

Numerical sensitivity testing over strain scale factors from 0.5 to 2.0
changed fitted \(\lambda\) only at approximately machine precision.

Therefore, a uniform template-based strain scaling factor cannot explain
the normalized-\(\lambda\) shift.

This does not imply that all possible digitization error is eliminated.

---

## 11.5 Model-free falsification

The Stage-1 to Stage-2 shift was reproduced directly using:

\[
y_{25},
\quad
y_{50},
\quad
y_{75},
\quad
\bar y_{10-90},
\]

without fitting the hyperbolic constitutive representation.

This is the strongest internal evidence that the observed shift is present
in the reconstructed laboratory curves themselves rather than being
created by the one-parameter model.

---

# 12. Candidate scientific contribution

The current defensible contribution is:

> **A paired within-specimen analysis of multistage unsaturated triaxial
> tests identifies a robust shift toward earlier normalized pre-peak
> stress mobilization from the first to the second loading stage in
> natural residual soils. The shift persists after stage-start stress
> rebaselining, alternative baseline definitions, tube-clustered
> uncertainty analysis, and separate MH and ML soil-class evaluation.**

The contribution is strengthened by combining:

- real laboratory data;
- explicit source provenance;
- curve-level reconstruction;
- constitutive parameterization;
- specimen-independent validation;
- paired within-specimen analysis;
- falsification tests;
- cluster-aware uncertainty; and
- model-free confirmation.

---

# 13. Novelty boundary

The project does **not** claim that any of the following are new:

- unsaturated multistage triaxial testing;
- loading-history effects in soils;
- normalized stress-strain analysis;
- hyperbolic stress-strain modelling;
- saturation-dependent constitutive behaviour;
- cyclic hardening;
- multistage versus single-stage differences.

The narrower candidate contribution is the quantitative,
within-specimen characterization and robustness testing of normalized
pre-peak mobilization evolution across consecutive unsaturated multistage
triaxial stages in this residual-soil archive.

No "first-ever" claim is made.

---

# 14. Limitations

The principal limitations are:

1. **Secondary dataset**

   The project analyzes an existing experimental archive rather than a
   purpose-designed laboratory campaign.

2. **Digitized curves**

   Full stress-strain histories were reconstructed from source PDF figures.

3. **Strain-axis confidence**

   Some curves use template-based strain-axis mapping rather than direct
   tick calibration.

4. **Normalized versus absolute strain**

   The strongest multistage finding concerns normalized mobilization.
   Absolute stiffness quantities require greater caution.

5. **Mechanism not isolated**

   The analysis identifies a response shift but cannot uniquely attribute
   it to fabric change, plastic strain accumulation, termination effects,
   or another physical mechanism.

6. **SC sample size**

   SC has insufficient independent-tube support for the same
   soil-stratified conclusion drawn for MH and ML.

7. **No general cyclic constitutive law**

   The compact hyperbolic representation does not replace advanced
   elastoplastic unsaturated-soil constitutive models.

8. **No boundary-value simulation**

   This is an element-test constitutive study, not a slope-scale FEM or
   multiphysics boundary-value model.

---

# 15. Figures

## Figure 01 — Primary finding

`results/figures/final/figure_01_normalized_mobilization.pdf`

Shows:

- mean normalized Stage-1 and Stage-2 response;
- tube-cluster bootstrap uncertainty;
- direct paired mobilization shift;
- principal effect-size descriptors.

---

## Figure 02 — Robustness

`results/figures/final/figure_02_robustness_and_soil_stratification.pdf`

Shows:

- sensitivity to alternative \(q_0\) definitions;
- MH versus ML stratification.

---

## Figure 03 — Constitutive representation

`results/figures/final/figure_03_constitutive_lambda.pdf`

Shows:

- mathematical meaning of \(\lambda\);
- near-monotonic relationship between \(\lambda\) and model-free
  mobilization;
- tube-paired Stage-1 to Stage-2 evolution of \(\lambda\).

---

# 16. Final project positioning

This project should be described as:

**laboratory-informed constitutive modelling and predictive analysis of
unsaturated residual-soil triaxial response.**

It demonstrates:

- experimental-data interpretation;
- unsaturated soil mechanics;
- constitutive modelling;
- inverse/parameter estimation;
- model validation;
- stress-path reasoning;
- uncertainty quantification;
- scientific falsification; and
- reproducible computational research.

It should **not** be described as:

- a new universal constitutive soil model;
- a fully coupled hydro-mechanical simulation;
- an experimental campaign performed by the project author; or
- proof of a specific microscopic mechanism.

---

# 17. One-sentence portfolio result

> **Reconstructed and constitutively analysed an unsaturated residual-soil
> triaxial archive, identifying a robust paired Stage-1 to Stage-2 shift
> toward earlier normalized pre-peak stress mobilization across 25
> multistage specimens from 18 independent tubes, with tube-clustered
> uncertainty, baseline sensitivity, soil-class stratification, and
> model-free falsification.**

