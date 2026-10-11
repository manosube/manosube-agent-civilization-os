# Preparing a tested package release

The improvement branch builds an sdist and wheel successfully. Quality CI also builds
the wheel on Linux, installs that wheel rather than an editable package, and exercises
the real initialization command and controlled canonical cycle. These artifacts are
candidates for review; they have not been uploaded to PyPI.

The branch retains the existing `1.0.1` metadata to avoid inventing a new accepted
release. Do not upload its changed wheel as the already published/released version.
Before publication, select a new version, update the package and release documentation,
rerun all required checks on that exact commit, and record an immutable tag and artifact
SHA-256 digests. Describe the new `init` command and Linux execution requirement in the
release notes and distinguish controlled examples from measured model effectiveness.

The owner must configure a PyPI project and publication credentials or trusted
publishing for the chosen workflow. Verify the project name and publisher identity,
publish the reviewed artifact, then install the published version in a clean Linux
environment and repeat the example. Record the package index URL and resulting receipts.
Keep tokens outside repository files. This branch neither supplies credentials nor
performs publication.

Release acceptance, PyPI availability and independent reproducibility are separate
outcomes. A successful package build alone establishes none of the latter two.
