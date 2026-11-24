# AEM deployment in Render

The existing `aem-demo-author` service watches `main` with automatic deployment disabled. Docker currently builds the Weather OSGi bundle with Maven and generates a mixed FileVault ZIP based on Adobe WKND 4.0.4. Both are installed from `crx-quickstart/install` when the container boots.

## Fast Deploy AEM

In [GitHub Actions](https://github.com/aribecker-demo-lab/aem-demo/actions), select **Fast Deploy AEM → Run workflow** on `main`. Set **baseline** to the full commit SHA of the last deployment you verified. Use the live Render commit if there have been no hot installs on the current container. Leave **install** unchecked to build and download the package only.

When **install** is checked, the job runs on the protected deployment environment `aem-demo`. Configure it under [Settings → Environments](https://github.com/aribecker-demo-lab/aem-demo/settings/environments). Restrict deployments to `main` and add these **environment secrets**.

- `AEM_DEPLOY_USER` and `AEM_DEPLOY_PASSWORD` for a dedicated AEM deployment account. Create it in [AEM User Management](https://aem-demo-author.onrender.com/security/users.html) and grant Package Manager access, the ability to upload and install in `/etc/packages/wknd-demo`, read the smoke-test page, and write to the package filter paths. Use the minimum permissions needed for those paths. The account and its permissions live in JCR and must be restored after an ephemeral replacement.
- Keep Author credentials out of the repository and GitHub variables. The installer uses HTTPS, refuses redirects, and only connects to the existing Author hostname. Production-grade ingress controls and durable identity are outside this setup.

Fast Deploy compiles and tests with Maven, generates a versioned FileVault ZIP and publishes a workflow artifact. It replaces only the project-owned `/apps` roots. For JCR content it compares the baseline and current generated packages, packages changed properties and new subtrees, and checks the live values before installation. It does not update unchanged properties or reinstall the Adobe WKND package. Review conflicts in Author before retrying. Coordinate content editing during installation because the conflict check and FileVault import are separate operations. Deletions, node-type changes, and binary replacements need a reviewed migration.

After installation, the workflow verifies the exact new bundle version in the Weather endpoint and a reversible HTML marker in the rendered Weather component. Build and install-to-smoke times appear in the workflow summary. No Render Deploy Hook is used in this workflow.

## Full Deploy AEM

Use this workflow for changes to Docker or the base runtime. In the [existing Render service settings](https://dashboard.render.com/web/srv-dc1oho59fdbs73be0n6g/settings), copy the **Deploy Hook**. Store it as `RENDER_DEPLOY_HOOK` in the GitHub environment `aem-demo-full`, restricted to `main`. The workflow triggers the existing service only and follows the latest commit on `main`. Check the deployment in the Render dashboard.

The service currently has no attached persistent disk. Hot installs and Author edits stay in the active JCR but can disappear when Render replaces its container. Back up Author-managed content and any hot changes before a full deploy. Persisting JCR on Render would require choosing and approving persistent storage and a mount and migration plan for the existing repository. Neither workflow provisions resources or attaches storage.

The previous full deploy took about 68 seconds to reach Render's live state, then several more minutes for AEM routes to become available. Compare that with the first authenticated Fast Deploy run before treating the time savings as measured.
