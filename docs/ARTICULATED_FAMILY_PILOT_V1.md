# Stage 2 — reusable articulated spider-family scaffolds

Five CPU runners build a **single shared GLB per public spider family** represented by an exact accepted-species name match, plus per-taxon adaptation research entries. Each family goes to one worker; duplicate cards should eventually reuse an approved species base.

## Implemented
- Hierarchically parented, individually named **56 rigid walking-leg segments across eight legs**, with pivots anchored in a generic prosoma. Two palp-root placeholders are separate.
- A neutral low-polygon blockout with one transform node per leg segment. It is *structurally poseable by changing node transforms*, but has no skin weights, inverse kinematics, motion limits or animation clips.
- Six camera research slots (metadata only), no rendered camera outputs.
- Per-taxon source-research queues, separate from human-approved private originals, sex and card mappings.

**Boundary:** Although grouped by biological family, the meshes use the *same unmeasured generic spider-order proportions for each family*. Nothing asserts scientifically correct Theraphosidae vs Salticidae morphology, nor species-specific joint measurements or mature-male diagnostics. All stages remain research-only with flags false for verified species/family morphology, anatomy approval and owner approval.

## Next production steps
1. Reconcile pending private 587-card PR #34, unique taxonomy, duplicate cards and explicit sex assignments.
2. Preserve Card 0016 V3 bare geometry and blue/copper appearance as separate immutable authorities; V3 remains anatomy-held.
3. Research primary taxonomic morphology and genuine same-species images; mark measured vs occluded vs structurally inferred joint positions.
4. Refine one true Theraphosidae archetype, validate on three distinct species and both sexes where evidence permits. Review limb roots, ocular topology, palps, spinnerets and uneven surface contact.
5. Add real pose controls and biomechanically constrained animations in Blender or another genuine rigging tool, then export optimised mobile GLB after scientific and human QA.
6. Connect private anatomy-gate CI with preview/reviewer without implicitly promoting candidates.

The public research workflow uses no paid model endpoint or native ChatGPT ImageGen. GitHub Actions' public hosted compute is free on standard runners subject to usage terms; artifacts expire after 7 days and storage is not unlimited.
