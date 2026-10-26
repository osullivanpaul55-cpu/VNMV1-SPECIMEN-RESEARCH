# VNMV1 five-lane 3D skeletal research — unapproved foundation

This isolated public workflow begins work toward **one evidence-backed digital animal per distinct species**. Multiple cards may share a verified species base, but every card-specific identity or human decision remains private. No original specimen photos, Human Gold annotations, personal Drive paths, or private card-number mappings are published.

## Five parallel CPU lanes
The five workers partition the existing **376 public taxon-name research leads** by sorted index modulo five. They use previously stored GBIF name-match records. Only exact accepted species-name matches from implemented orders receive a bare neutral 3D **geometry blockout**. All other names produce explicit hold records.

The initial meshes consist of body proxies and named walking-leg segments. They are **NOT skinned/poseable rigs**, **NOT measured species-specific morphology**, **NOT sex-verified**, and **NOT biological approval**. No eye arrangement, mature-male emboli, tibial spur, spinneret microanatomy, wing structure, hairs, colours, or textures may be inferred from these outputs. Centipedes and unknown orders are held until their own body plans are researched. Scorpion/amblypygid/insect templates are especially coarse and will require replacement with proper family anatomy.

## Next steps

1. Reuse the existing research photo and literature candidates to build source-bound measurements, with confidence and source-individual grouping. Links are research leads, not evidence that the pixels were passed to an image model.
2. Create vetted *family-specific* articulated parent-child skeleton rigs, then evaluate joint degrees of freedom and all poses. Preserve the current Card 0016 V3 as an anatomy-held prototype, not a master.
3. Adapt those family rigs to distinct species, sex and life stage using real measurements when available. Do not copy 0016 lengths to other taxa.
4. Bridge public taxon-level drafts into the private 587-card registry **only** through a private read-only mapping that preserves identity conflicts and originals. As of 26 Oct 2026 the 587-card readiness roster was on unmerged VNMV1_CORE PR #34.
5. Export reviewed, mobile-optimised GLBs, anatomy QA plates and later textures/animations for human approval. Integrate the private skeleton gate; never auto-promote.

## To run

GitHub repository Actions -> **Five public anatomy blockout and research runners** -> **Run workflow** on main. A push of the workflow to main is also configured. Each of five workers uploads short-lived draft GLB artifacts and a manifest; this does not connect paid model APIs or ChatGPT ImageGen. GitHub Actions may be delayed, rate-limited or unavailable.

This workflow covers existing public research-name leads only, **not all 587 card identities**, and even successfully exported neutral geometry remains **UNAPPROVED**.
