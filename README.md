# VNMV1 Specimen Research — Public-Safe Research Repository

This is the **public component only** of the VNMV1 natural-history reference research programme. It contains 195 *candidate research species names* from an existing 526-card research roster, five no-paid-model photo research workers, provenance/copyright filters, durable GitHub Release archive assets, a mobile-friendly human review webpage, and unit tests. It contains **no original card specimen photographs, Human Gold annotations, per-card species/sex mapping, personal Google Drive data, paid API credentials or image-generation executor**.

**WARNING: All photos are unapproved research candidates**, regardless of community research-grade status. Do not assert specimen sex, exact species identity, licence fitness for a particular commercial AI workflow, or approval to generate from any public index field. The public queue never makes those decisions.

## Public research workflow

- GitHub Actions workflow: `.github/workflows/research-five.yml` — five parallel CPU research jobs, typically four unique species per worker and up to 18 distinct, licence-screened photo frames per species (including several distinct angles from one observation when present). Discovery checks up to eight iNaturalist pages per query; images now prefer the larger public JPEG derivative when available. Download checks valid pixels, attribution, file hashes and apparent near-duplicates. Actual biological suitability, sex and licensing terms still require your review.
- Every completed run publishes five GitHub **Release ZIP assets**, plus a credits manifest, not just expiring Actions artifacts. The public `data/index.json` links to these archived ZIPs and contains SHA-256 hashes and source URLs; `review/index.html` offers visual/biological review. Release archives remain available while the project and those Releases are maintained; this is **not an unconditional permanence or unlimited-storage guarantee**. Mirror important approved assets separately.
- The GitHub Actions artifacts are short-lived transport buffers (seven days). **Release ZIPs** are the durable public candidate archive.
- If named taxa are exhausted, the workflow revisits for more sources. It never fabricates missing six-photo female or male sets.
- Species pools share research across multiple private cards, but the mapping remains private. 236 of 526 cards currently lack a usable research-species key in the separate private roster; they are explicitly unresolved, not magically covered by 195 species research queries.

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

## Licence and data separation

Only iNaturalist photo candidates with **photo-level** CC0 or CC BY codes are downloaded. Research grade is community ID evidence only; CC metadata is not a legal review. Preserve attribution and original link with every redistributed photograph. *Do not assume a CC BY 4.0 licence version unless the photo/source explicitly supports it*. Licence terms, photographer claims, and downstream model use require human review. Code in this repository is separate from the photographers' licences.

No open-source licence is automatically applied to photographs by this repository. Each photo retains the original photographer's licence requirements and attribution record in its Release archive.

## Review

Open the site `/review/` (GitHub Pages) on a phone; filter by scientific name; inspect original observation links; mark `Accept female`, `Accept male`, `Structural only`, `Needs more evidence` or `Reject`; correct anatomy and source information in notes. Accept selections require species and licence confirmations. The browser stores unfinished decisions locally; **Export decisions** downloads a review JSON. Upload it back to the private review/import process. No user decisions are sent automatically to GitHub, no original or private card files are published, and no model images are generated.

## Safety testing

```sh
python -m pip install Pillow
python -m unittest discover -s tests -p 'test_public_research.py' -v
```

Research output is not a model input until private-side biological and rights checks pass; the eventual ImageGen executor remains a separate engineering project.