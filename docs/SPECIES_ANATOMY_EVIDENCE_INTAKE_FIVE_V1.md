# VNMV1 species-bound anatomical research intake (public five-runner integration)

The existing five public photo researchers already discover and sometimes archive real source-photo bytes, retaining URLs, observation IDs, SHA-256 digests, photographer credits and rights claims. The new stage **does not perform another image search**: it converts each shard's candidate outputs into species-labelled **unreviewed photo evidence leads**.

Source: `research/collect.py`. New converter: `research/species_anatomy_evidence_intake_v1.py`. Workflow: `.github/workflows/research-five.yml`. Every newly collected photo remains a candidate: a valid SHA-256 means that downloaded bytes were decoded and hashed, **not** that the photo shows a certain leg joint, life stage or biological species. Two files from one observation are not counted as two independent organisms. Link-only research results have no claimed pixel hash or copied media.

The strict species doctrine is authoritative in the private production repository `osullivanpaul55-cpu/VNMV1-FLUX-Docker-Build/authority/VNMV1_SPECIES_BOUND_ANATOMY_DOCTRINE_V1.json`. This PUBLIC implementation mirrors the protective states without bringing the user's private identity mapping, original specimens or Human Gold evidence into this repository.

## Source and anatomy status

Each entry retains: `research_taxon_lead`, observation source URL and grade, source photo digest if collected, observation grouping, `sex_stage=UNKNOWN`, `camera_pose=UNREVIEWED`, zero reviewed joints, zero anatomy approvals, and `unknown_leg_article_lengths_mm` values set to null. Cross-taxon candidate records, forged source URLs, or public self-approvals cause a hard error.

The workflow appends `ANATOMY_EVIDENCE_INTAKE_V1.json` to each photo-research shard and, for new runs, includes the same research-only record in the corresponding public ZIP Release archive. Existing published releases remain unchanged.

The private 587-card roster must be mapped **after this stage**, in a private repository. Exact name matches are candidate lookups, not evidence that a photograph matches the user's original card; human anatomical/photo review and independent multi-view examination are mandatory. A public research lead can never unlock a species mesh or master by itself. The earlier generic 3D blockouts and family-prototype GLBs remain unapproved.
