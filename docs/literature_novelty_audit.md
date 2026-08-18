# Literature Novelty Audit

## UnsatConstitutiveLab

### Candidate contribution

A paired within-specimen analysis of multistage unsaturated
triaxial tests reveals a systematic shift toward earlier normalized
pre-peak stress mobilization from the first to the second loading
stage in natural residual soils.

The observed shift persists after:

- stage-start stress rebaselining;
- alternative definitions of stage-start stress;
- normalization by stage-specific peak stress and peak strain;
- tube-clustered paired bootstrap analysis; and
- separate analysis of MH and ML soil subsets.

This is treated as a **candidate contribution**, not yet as a claim
of first-ever discovery.

---

## Core definition

For each shearing stage,

\[
x = \frac{\varepsilon_a}{\varepsilon_{a,p}}
\]

and

\[
y =
\frac{q-q_0}
     {q_p-q_0}.
\]

Here:

- \(q_0\) is the stage-start deviator-stress baseline;
- \(q_p\) is the stage-specific peak deviator stress;
- \(\varepsilon_{a,p}\) is the stage-specific peak axial strain.

The primary comparison is paired within specimen:

\[
\Delta y(x)
=
y_{\mathrm{stage\,2}}(x)
-
y_{\mathrm{stage\,1}}(x).
\]

A positive value means that the second stage mobilizes a larger
fraction of its stage-specific peak stress increment at the same
normalized strain.

---

## Locked primary result

For 25 stage-1/stage-2 specimen pairs representing 18 independent
tubes, the second stage showed consistently earlier normalized
mobilization.

Using the primary 5% \(q_0\) definition:

- \(\Delta y_{25} = +0.162\)
- 95% tube-cluster bootstrap interval:
  +0.115 to +0.209

- \(\Delta y_{50} = +0.171\)
- 95% tube-cluster bootstrap interval:
  +0.132 to +0.210

- \(\Delta y_{75} = +0.085\)
- 95% tube-cluster bootstrap interval:
  +0.065 to +0.105

- \(\Delta \bar y_{10-90} = +0.131\)
- 95% tube-cluster bootstrap interval:
  +0.100 to +0.161

The direction and practical magnitude persist when \(q_0\) is
estimated over 2%, 5%, 10%, and 15% of peak strain.

The effect is independently present in the MH and ML subsets.

SC is not assigned the same conclusion because the available
independent-tube count is insufficient for a comparable
soil-stratified inference.

---

## Hyperbolic representation

A compact normalized pre-peak representation is

\[
\frac{\Delta q}{\Delta q_p}
=
\frac{x(1+\lambda)}
     {1+\lambda x}.
\]

The fitted mobilization parameter \(\lambda\) strongly tracks
model-free normalized-curve descriptors.

However, the main scientific result is stated using direct
nonparametric mobilization quantities \(y_{25}\), \(y_{50}\),
\(y_{75}\), and \(\bar y_{10-90}\).

Therefore, the finding does not depend on the validity of the
one-parameter hyperbolic description.

---

# Closest literature

## Ho and Fredlund (1982)

D. Y. F. Ho and D. G. Fredlund,
"A Multistage Triaxial Test for Unsaturated Soils,"
Geotechnical Testing Journal, 5(1/2), 18-25.

DOI:
https://doi.org/10.1520/GTJ10795J

Relevance:

- early unsaturated multistage triaxial methodology;
- intended primarily for characterization of suction-dependent
  shear strength.

Implication for novelty:

Multistage testing of unsaturated soils is not novel.

---

## Khosravi et al. (2012)

A. Khosravi, N. Alsherif, C. Lynch, and J. S. McCartney,
"Use of Multistage Triaxial Testing to Define Effective Stress
Relationships for Unsaturated Soils,"
Geotechnical Testing Journal, 35(1).

DOI:
https://doi.org/10.1520/GTJ103624

Relevance:

- multistage unsaturated triaxial testing;
- effective-stress and shear-strength interpretation.

Implication for novelty:

Use of loading stages to characterize unsaturated mechanical
response is established.

---

## Banerjee et al. (2018)

A. Banerjee, A. J. Puppala, U. D. Patil, L. R. Hoyos,
and P. Bhaskar,
"A Simplified Approach to Determine the Response of Unsaturated
Soils Using Multistage Triaxial Test,"
IFCEE 2018, GSP 295, 332-342.

DOI:
https://doi.org/10.1061/9780784481585.033

Relevance:

- termination criteria for initial multistage shearing stages;
- comparison with conventional testing;
- similar shear-strength parameters were obtained.

Implication for novelty:

General comparison of single-stage and multistage response is
not novel.

---

## Banerjee, Puppala, and Hoyos (2020)

A. Banerjee, A. J. Puppala, and L. R. Hoyos,
"Suction-controlled multistage triaxial testing on clayey silty
soil,"
Engineering Geology, 265, 105409.

DOI:
https://doi.org/10.1016/j.enggeo.2019.105409

Relevance:

- suction-controlled single-stage and multistage comparisons;
- explicit comparison of deviator-stress responses;
- focus on termination procedure and reliability of multistage
  strength determination.

Implication for novelty:

A statement such as "multistage stress-strain curves differ" is
too broad to claim as novel.

The present candidate contribution must instead be framed around
paired, within-specimen, normalized pre-peak mobilization
evolution and its quantified robustness.

---

## Tang, Borden, and Gabr (2019)

C.-T. Tang, R. H. Borden, and M. A. Gabr,
"Model applicability for prediction of residual soil apparent
cohesion,"
Transportation Geotechnics, 19, 44-53.

DOI:
https://doi.org/10.1016/j.trgeo.2019.01.003

Dataset DOI:
https://doi.org/10.17632/p9tmzckdpt.1

Relevance:

- source study and source dataset;
- natural/undisturbed residual soils;
- MH, ML, and SC materials;
- paper focus: suction-dependent unsaturated shear strength and
  apparent cohesion;
- paper reports 19 unsaturated triaxial tests:
  8 single-stage and 11 multistage.

Implication for novelty:

The current project is a secondary analysis of the source
experimental archive.

It must not imply that the original paper reported the present
full-curve finding.

---

## Soranzo (1988)

M. Soranzo,
"Results and Interpretation of Multistage Triaxial Compression
Tests,"
ASTM STP.

DOI:
https://doi.org/10.1520/STP29086S

Relevance:

- multistage triaxial interpretation;
- normalized stress versus strain;
- normalized tangent modulus;
- hyperbolic interpretation.

Implication for novelty:

Normalization and hyperbolic representation are established
tools and are not themselves contributions of the present work.

---

## Chen et al. (2024)

L. Chen, J. Ghorbani, T. T. Dutta, A. Zhou,
J. S. McCartney, and J. Kodikara,
"A new multi-surface plasticity model for cyclic hardening of
unsaturated granular soils,"
Computers and Geotechnics, 173, 106500.

DOI:
https://doi.org/10.1016/j.compgeo.2024.106500

Relevance:

- advanced unsaturated cyclic constitutive modelling;
- generalized kinematic hardening;
- repeated-load behaviour;
- hydraulic-state effects.

Implication for novelty:

Generic statements such as "loading history matters" or
"unsaturated soil exhibits cyclic hardening" are not novel.

The current project does not propose a competing general cyclic
plasticity law.

---

# Claim boundaries

## Supported

The data support:

> Under the investigated multistage unsaturated triaxial protocol,
> the second shearing stage mobilized a systematically larger
> fraction of its stage-specific peak deviator-stress increment at
> the same normalized axial strain than the first stage within the
> same residual-soil specimen.

The result is robust to:

- stage-start stress definition;
- peak-strength normalization;
- uniform strain-axis scaling;
- hyperbolic versus direct model-free characterization;
- tube clustering;
- MH versus ML stratification.

---

## Not supported

Do not claim:

- a new universal constitutive law;
- first-ever observation of loading-history effects in
  unsaturated soil;
- intrinsic cyclic hardening;
- causal fabric evolution;
- a general law for all residual soils;
- validity for SC based on the present soil-stratified sample;
- equivalence of multistage and virgin single-stage deformation
  response;
- that the Tang et al. paper reported this finding.

---

# Current novelty assessment

The literature audit does not establish a first-ever discovery.

However, the closest identified literature primarily addresses:

1. multistage testing methodology;
2. termination criteria;
3. shear-strength/effective-stress equivalence;
4. single-stage versus multistage validation; or
5. general cyclic constitutive hardening.

A narrower contribution remains credible:

> quantitative paired within-specimen characterization of the
> evolution of normalized pre-peak stress mobilization between
> consecutive stages of unsaturated multistage triaxial tests on
> natural residual soils, supported by model-free descriptors,
> tube-clustered uncertainty analysis, baseline sensitivity, and
> soil-class stratification.

This wording should be retained unless a closer prior study is
identified.

---

# Next project phase

Exploratory hypothesis generation is closed.

Remaining work:

1. publication-quality result figures;
2. final constitutive formulation and terminology;
3. compact methods/results write-up;
4. limitations and provenance statement;
5. README and repository polish;
6. CV and PhD-application wording.

