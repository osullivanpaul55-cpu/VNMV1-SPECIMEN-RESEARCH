# VNMV1 pose-aware candidate research V1

**Purpose:** extend the existing five-shard public photo researchers with systematic view coverage. A photograph count is NOT a view-coverage count.

## Standard pose vocabulary

Core six: `FRONTAL`, `WALKING_AWAY_REAR_OBLIQUE`, `LATERAL_PROFILE`, `OBLIQUE_THREE_QUARTER`, `DORSAL_TOP_DOWN`, `POSTERIOR`.

Optional evidence-led views: `ELEVATED_ALERT`, `DEFENSIVE_THREAT`, `VENTRAL_UNDERSIDE`, `VERTICAL_CLIMB`.

Six is the standard camera plan; optional views depend on animal type, habitat, sex/stage and genuine photographic evidence. Not every species or individual should be forced into a threat pose or ventral exposure. The private pack compiler remains responsible for animal-type and sex-specific suitability.

## Research and verification flow

1. Public researchers query up to eight pages of iNaturalist observations for each accepted *research name candidate*, download up to 18 distinct frames per species per run and revisit species in later cycles. They may retain up to three visually distinct frames from one observation because those may cover different viewpoints, but these frames are **not three different individual spiders**.
2. The observation description can supply `unverified_observer_text_pose_hints`; it **does not** classify photographs automatically. No iNaturalist observation, community grade, camera-text match or pose label proves sex, original specimen identity or license suitability.
3. Each photo enters the public index with `pose_id: UNREVIEWED`. The mobile review page permits a reviewer to assign a single primary camera pose. The exported decisions preserve `pose_id` and SHA-bound candidate identity even when the biological decision remains PENDING.
4. The private authority/importer combines review labels, same-species/sex authorization, SHA-256 verified image bytes, legally suitable image rights, and focal-card references. It must calculate **per-variant pose coverage** and prioritize missing views. Public research never turns a pose label into a generated photograph or a production approval.
5. Each actual model call still contains **one specimen, one morph, one pose, one photograph**. The resulting synthetic master goes through independent anatomical and alpha QA. Do not supply contact sheets, pose-reference research documents, or multi-output dashboards as production model inputs.

## Species photo-reference coverage floor

For each distinct named species or evidence-supported candidate taxon, seek **at least 9 distinct individual photo/source records** from reputable web sources where they can be found. Aim for 12 and preferably 12–15; the review app can hold up to 18 candidate records per taxon. This is a reference-coverage target, not a species-identity or ImageGen-rights approval.

Count an archived candidate photograph or a direct, individual source-photo/observation lead once, after deduplication. Do not count search-result pages, general browse links, text-only pages, illustrations, synthetic images or duplicate photographs. The reviewer must open and assess each source record; unknown or restricted rights may remain a link-only research lead.

If fewer than nine suitable references can be found, preserve the search trail, record the count and why the source pool is limited, and leave the taxon visibly below target. Do not invent, duplicate or silently substitute images. A genuine user-reviewed photo can still establish card identity at the taxonomic rank it supports; a documented coverage shortfall does not by itself invalidate that identity decision. Sex, life stage, behaviour and image-use rights remain separate.

## Fair coverage metric

Measure eligible pose coverage as **distinct reviewer-confirmed pose IDs** from eligible source images, not by counts of photos or iNaturalist records. Require a stronger visual reference for ventral/sex-diagnostic anatomy and mature-male emboli/palp/spur depiction; otherwise hold that exact view or detail as unknown. Exact high-resolution source originals and verified same-species/sex photographs rank above related-species comparisons.

Public data are only generic taxa/photo candidate records. **Never copy private card IDs, original image bytes, Human Gold files, or source specimen sex** to this public repository.

## Cost control and limits

No paid APIs, GPU use, background ChatGPT-native ImageGen invocation or training are included. A daily Actions schedule may consume GitHub Actions minutes and Release storage; repository owners should check their included quota. Broadening public-source discovery does not guarantee that every view exists publicly or that its photograph is legally usable.

## Outstanding integration

Private packet compiler must ingest human decisions/export, keep accepted view-tagged photo identity separate from unapproved candidates and emit a per-card / per-sex missing-pose research queue; the old six-photo V3 gate and provider attestation remain closed until explicitly migrated and tested.
