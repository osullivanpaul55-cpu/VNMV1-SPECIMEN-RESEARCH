# Stage 3 — Theraphosidae evidence-calibrated anatomical study (2026-10-26)

The purpose is to replace unqualified placeholder sizes with at least one published, voucher-bound anatomical measurement profile, without pretending the entire 587-card collection or any other taxon inherits that individual's lengths.

## Source-validated anatomy
- The American Museum of Natural History's spider morphology guide defines the 7 named walking leg segments, 8 walking legs, separate pedipalps, chelicerae, prosoma, pedicel and opisthosoma: https://www.amnh.org/learn-teach/curriculum-collections/biodiversity-counts/arthropod-identification/arthropod-morphology/parts-of-a-spider-dorsal-view-of-a-male-spider
- Hamilton, Hendrixson & Bond 2016, ZooKeys 560 (primary paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4768370/) reports a preserved adult female Aphonopelma eutylenum specimen, voucher APH_1031, including 16.55 mm long and 15.05 mm wide carapace, and specific left leg I, III and IV femur–tarsus measurements.
- Those 15 measured distal lengths are encoded exactly for the left legs in research/data/theraphosidae_morphometry_evidence_v1.json and applied to a neutral 3D reference for APH_1031 only.
- The right limbs are geometric reflections of the left, not measured right limbs; leg II, all coxae and trochanters, 3D orientations, abdomen depth, feet and pose remain unmeasured placeholders.
- The 56 named links are a geometric rig hierarchy. This does not certify realistic motion, anatomical soft tissue, full three-dimensional reconstruction or living behaviour. No animations, skinning, texture, hairs or biologically checked camera outputs.
- Two comparative studies show why a single body or setal pattern cannot describe all tarantulas: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0087928 and https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0224384

## Hard gates
- No copying APH_1031 lengths into Aphonopelma mooreae, Card 0016, or any other species.
- Female study contains no invented mature-male bulbs, emboli, tibial apophyses or eight-eye coordinates.
- No claim that live joint angles or foot positions were measured from museum-preserved body-part metrics.
- Future taxon-specific models require genuine multi-angle species photographs, specimen research, and independent human review.
- Preserve Card 0016 V3 provisional skeleton and blue/copper appearance; neither is altered by this public study.

## Running
python research/theraphosidae_measured_exemplar_v1.py --out out/theraphosidae-aph1031

The GitHub workflow exports a neutral GLB and an audit JSON. This source-calibrated exemplar is a research advance, not yet a certified family geometry model or a production-ready species mesh.
