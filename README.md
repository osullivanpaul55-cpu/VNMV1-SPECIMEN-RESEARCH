# VNMV1 Specimen Research — Public-Safe Research Repository

This is the **public component only** of the VNMV1 natural-history reference research programme. It contains an unchanged 195-name base seed plus a separate 73-name species/subspecies extension and four unresolved genus/locality research units for an existing 526-card research roster, five no-paid-model photo research workers, provenance/copyright filters, durable GitHub Release archive assets, a mobile-friendly human review webpage, and unit tests. It contains **no original card specimen photographs, Human Gold annotations, per-card photo-level identity or sex verification, personal Google Drive data, paid API credentials or image-generation executor**.

The public reviewer now includes the best available card identity label from prior project reconciliation for all 526 card IDs. Labels retain the source's formal, informal, higher-taxon, or conflict level and do not verify the individual card photograph.

**WARNING: All photos are unapproved research candidates**, regardless of community research-grade status. Do not assert specimen sex, exact species identity, licence fitness for a particular commercial AI workflow, or approval to generate from any public index field. The public queue never makes those decisions.

## Public research workflow

**Pose and behaviour research V2:** each candidate remains `pose_id=UNREVIEWED`, with any observation-description pose or behaviour phrases labelled as **unverified text leads**, never visual conclusions. Within a run, candidates from distinct observations are prioritised before additional frames of the same observation. This helps gather broader camera and behaviour evidence (walking, burrow emergence, feeding, defensive postures, climbing, moulting, courtship, grooming and silk), but does not promise that these activities are pictured. The five CPU workers still have no access to the private Gold cards or app.

**Reruns:** GitHub Actions has a manual `workflow_dispatch` input, a daily schedule, and an explicit versioned request file route `research/run_requests/*.json`. Each new **file** committed under that directory on `main` triggers one standard five-shard research round (subject to GitHub Actions schedule and permissions). Only create a request when needed: each run consumes included GitHub Actions compute time and Release storage. Avoid retriggering by editing old requests.


- GitHub Actions workflow: `.github/workflows/research-five.yml` — five parallel CPU research jobs, twelve unique taxa per worker by default (up to 60 per cycle), and up to 18 photo candidates per taxon per pass. A separate five-runner identity workflow maps all 376 distinct public roster taxon labels; only exact accepted species matches absent from the existing catalog are added to photo research. Discovery checks up to eight iNaturalist pages for exact species-level community taxa across Research Grade, Needs ID and Casual observations; the grade is retained for review and never treated as expert or owner approval. When a taxon still has room below the 15-reference review cap, the worker also searches GBIF occurrence records with still-image media and Wikimedia Commons file pages by species-name text. GBIF occurrence records can include a second link to the underlying photo source; Commons hits remain file-page links. Both source types are flagged as unverified taxon/photo matches, and their attribution and licence claims need your review. After the full first sweep, later cycles prioritize taxa below 9 references, then gaps to 12 and 15, with least-recently-researched taxa first. Only photo-level CC0/CC BY iNaturalist candidates enter the downloadable archive; all GBIF and Commons hits and other or unknown rights remain source links. Image decoding, attribution, hashes and near-duplicates are checked, while biological suitability, sex and licensing terms still need your review.
- Every completed run publishes five GitHub **Release ZIP assets**, plus a credits manifest, not just expiring Actions artifacts. The public `data/index.json` links to these archived ZIPs and contains SHA-256 hashes and source URLs; `review/index.html` offers visual/biological review. Release archives remain available while the project and those Releases are maintained; this is **not an unconditional permanence or unlimited-storage guarantee**. Mirror important approved assets separately.
- The GitHub Actions artifacts are short-lived transport buffers (seven days). **Release ZIPs** are the durable public candidate archive.
- If named taxa are exhausted, the workflow revisits for more sources. It never fabricates missing six-photo female or male sets.
- Species pools share research across cards. The public registry now has a card identity label for all 526 card IDs; 236 still lack a shared research-species key, and informal, higher-taxon, or disputed labels retain their recorded level. Card labels do not establish that the original photo or individual specimen was verified.

## Deployment status — 21 October 2026

The fresh-history PUBLIC repository is now created and deployed. The first five-runner execution passed and published 157 **unapproved** candidates across 20 research species into five public Release ZIPs. Research runs automatically every day at the scheduled UTC time, subject to GitHub Actions availability. The PRIVATE VNMV1 production importer is connected and succeeded; private original specimen photos and card mappings remain outside this public repository. No biological or licence approval, and no image generation, has occurred.

**Phone review website:** GitHub Pages still needs to be enabled manually in this new repository's Settings → Pages → Build and deployment → Source → GitHub Actions. The automatic enablement workflow is refused by the repository-scoped Actions token. After enabling Pages, manually rerun the 'Publish specimen photo review webpage' workflow or allow the next index update to publish it.

## How to activate

1. This repository is a dedicated public, fresh-history research repository named `VNMV1-SPECIMEN-RESEARCH`. Do not turn the existing private `VNMV1-FLUX-Docker-Build` repository public. A separate public repo should be created with a **fresh history**.
2. Add these public-safe folder contents to that new repository's `main` branch. Do **not** upload any `/private` directory or combined project ZIP. A connected GitHub owner can author the files after the repository exists and the GitHub connection has access to it.
3. In repository Settings → Actions → General, allow workflows and the repository-scoped `GITHUB_TOKEN` to write Releases/index commits, consistent with your account policy.
4. In Settings → Pages set **Build and deployment → Source → GitHub Actions** to enable the review page. The `pages.yml` workflow publishes `/review/` from static files; public site address is supplied by GitHub after deployment.
5. Trigger Actions → **Five public specimen reference researchers** → Run workflow. An automatic daily schedule is included; scheduled jobs can be delayed or skipped by the provider.
6. Connect the existing private repository by setting its repository variable `VNMV1_PUBLIC_RESEARCH_REPO` to `osullivanpaul55-cpu/VNMV1-SPECIMEN-RESEARCH` (or the actual owner/name). Only the **private** importer may associate photos with user cards or Human Gold.

## Research immediately when a photo has no licence metadata

The five workers now **include missing or restrictive photo-licence references as link-only research leads** in each species entry (`link_only_leads`). These can be searched, grouped by species, and opened from the mobile review website immediately—no permission check is needed just to retain the citation and ask a researcher to inspect the original public source. Observer descriptions are unverified hints, not verified pose/sex evidence.

Unknown/right-restricted source photos are **not downloaded, copied into public Release ZIP files, or promoted to image-generation inputs**. When a source exposes a direct image URL, the review page loads that source-hosted image inline for inspection and shows its source, attribution and licence details. This remote preview is not a copy or approval for redistribution or ImageGen; sources that block inline display retain an open-original link. Photo-level CC0/CC BY candidates continue through the downloadable archive lane.

The mobile website separates **Archived photo candidates** from **Research-only photo links**; users can open the latter and assess pose or anatomy at the source. The installed Gold Android APK remains a separate integration.

## Licence and data separation

Only iNaturalist photo candidates with **photo-level** CC0 or CC BY codes are downloaded. Research grade is community ID evidence only; CC metadata is not a legal review. Preserve attribution and original link with every redistributed photograph. *Do not assume a CC BY 4.0 licence version unless the photo/source explicitly supports it*. Licence terms, photographer claims, and downstream model use require human review. Code in this repository is separate from the photographers' licences.

No open-source licence is automatically applied to photographs by this repository. Each photo retains the original photographer's licence requirements and attribution record in its Release archive.

## Review

Open the site `/review/` (GitHub Pages) on a phone; filter by scientific name; inspect inline source-hosted previews or open the original observation pages; mark `Accept female`, `Accept male`, `Structural only`, `Needs more evidence` or `Reject`; correct anatomy and source information in notes. Accept selections require species and licence confirmations. The browser stores unfinished decisions locally; **Export decisions** downloads a review JSON. Upload it back to the private review/import process. No user decisions are sent automatically to GitHub, no original or private card files are published, and no model images are generated.

## Safety testing

```sh
python -m pip install Pillow
python -m unittest discover -s tests -p 'test_public_research.py' -v
```

Research output is not a model input until private-side biological and rights checks pass; the eventual ImageGen executor remains a separate engineering project.

## 25 October — expanded photo review catalog

The unchanged 195-name seed is combined at runtime with `research/species_reference_extension.json`: 73 named species/subspecies research taxa from the new intake plus four locality-level research units whose identities remain unresolved. The extension adds source-search links for every taxon and 65 individual photo/source pages as link-only leads. Search pages are browse links, not individual photo reviews. All supplied images, rights claims, sex, stage, pose and taxon assignments remain unverified until a human reviews the source.

Research cycles can collect up to 18 candidate photographs per taxon per pass. Collection uses the existing CC0/CC BY pixel archive rules; sources with other or unknown rights remain source links. The extension is inserted at the next research position so the first cycles prioritize the new intake without changing the original seed file or its established ordering.
