# Build and verify portable bundles

This operator workflow creates local artifacts; it does not publish a release,
create a tag, upload files or submit a catalog entry. Published preview bundles are available from the
[GitHub releases page](https://github.com/rbur0425/ownmachine/releases).
The first preview is v0.6.0.

## Build from an exact commit

Use a clean checkout with Git and Python 3.10 or later. Commit all intended source
changes first. Choose a new output directory with an existing parent, outside the
checkout:

```sh
python3 scripts/release-bundle.py build --output-dir /absolute/path/to/new-bundle-directory
```

The builder uses the full `HEAD` commit, never files copied from a running install.
Tracked changes and untracked non-ignored files cause refusal. Ignored local keys,
VM disks, Python caches and runtime files are excluded because only Git archive
content is read. **A secret already committed to Git would still be packaged.**
Review the commit and inventory before distribution; this is not a secret scanner.
Symlinks, submodules and unsupported archive entries are refused. Output is never
written inside source and existing output directories are never overwritten.

The output contains:

| Artifact | Contents |
| --- | --- |
| `ownmachine-plugin-FULL_SHA.tar.gz` | Only the contents of `plugin/`, plus the project license; no host scripts, viewer, noVNC or operator dependencies. |
| `ownmachine-source-FULL_SHA.tar.gz` | Committed source, documentation, tests, operator scripts, vendored noVNC and all its license notices; no `.git` directory. |
| `manifest.json` | Exact source commit, artifact hashes/sizes and per-file hashes, sizes and executable flags. No build-machine paths or host identities. |
| `SHA256SUMS` | SHA-256 checksums of both archives and the manifest. |

Tar entries are sorted with normalized timestamps, owners and executable modes;
gzip has a fixed timestamp and no filename. Repeated builds from the same commit
with the same Python/zlib implementation are byte-identical. Compression library
changes may affect compressed bytes; compare inventories as well as tool versions
when investigating cross-environment differences. No timestamp, hostname or
private deployment configuration is added to metadata.

## Verify before extraction

Use the verifier from a separately trusted checkout:

```sh
python3 scripts/release-bundle.py verify --bundle-dir /absolute/path/to/bundle-directory
```

Verification checks artifact checksums, complete file inventories, safe archive
paths/types and the plugin boundary, without extracting or executing contents.
It rejects oversized artifacts, symlinks, duplicate files and path traversal.
Exit 0 means integrity checks passed; exit 1 means refusal or failure. Checksums
are **not signatures**: an attacker able to replace the archives and manifest can
replace their hashes too. Obtain the expected commit and checksums through a
trusted distribution channel. Never run an untrusted bundled verifier as proof
that its own bundle is trustworthy.

After verification, extract the source archive into a new empty directory and
follow [community setup](community-setup.md). The fresh-home installer preserves
operator-owned configuration and refuses existing homes. In an exported checkout,
its existing receipt records exact installed file hashes but no Git revision;
keep the bundle manifest beside the deployment receipt to identify the source.
The source includes the noVNC onboarding guide and dependencies; the plugin-only
archive does not automate host, guest, viewer or firewall installation.

For plugin-only manual installation, extract its contents into a new
`plugins/ownmachine` directory under the intended Hermes home, then validate that
exact directory with `hermes plugins validate`. Configure it using the native
provider guide. Do not extract the full-source bundle into Hermes's plugin path.
Upgrading an active installation remains an explicit operator workflow with a
rollback copy; this tool never changes a running installation.

## Before an actual release

Run the full tests and Hermes plugin validation on the exact candidate commit,
then validate the extracted plugin artifact too. Retain checksums and sanitized
validation evidence. A source archive must retain third-party notices. Review
[release readiness](release-readiness.md) and [security boundaries](../SECURITY.md).
Public catalog metadata still needs a real distribution URL, full commit and
current admission validation; placeholders are not submission-ready metadata.

## Licensing

Distribution of the updated source and future bundles is subject to PolyForm
Noncommercial License 1.0.0. Use, modification and redistribution are allowed for
its permitted purposes, with its notices retained. Commercial use outside those
permissions requires a separate license. Third-party terms remain intact.
Previously published artifacts retain their original licenses; see
[licensing details](licensing.md).
