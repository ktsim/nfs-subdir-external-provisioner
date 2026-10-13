# Evaluation of the supplied Claude recommendations

The supplied text files were reviewed as recommendations, not executed as instructions.

| Aspect | Minimal recommendation | Master recommendation | Aligned patch |
| --- | --- | --- | --- |
| Source | Upstream v4.0.2 | Moving master branch | Upstream v4.0.2 |
| HTTP/2 module | x/net v0.17.0 | Master dependencies | x/net v0.17.0 |
| Go toolchain | Floating golang:1.26 | Upstream build | Go 1.26.9, builder digest pinned |
| Kubernetes/provisioner dependencies | Intended unchanged | Broad upgrades | Unchanged; only required x/net companion modules resolve newer |
| Runtime | Original v4.0.2 image | Alpine 3.23 | Exact original v4.0.2 image digest |
| Old binary layers | Podman --squash-all | Fresh image | One-layer archive; Linux recipe requires --squash-all |
| Publication | Automatic push | Automatic push | Local archive; explicit registry publication later |

The minimal recommendation addresses the same vulnerability as the original patch.
The master recommendation is unsuitable for the requested minimal change because
it also updates application/dependency versions and changes the runtime.

Improvements over the supplied minimal script:

- Dependency selection and checksums are reviewed in Git before the build;
  no `go get` or `go mod tidy` runs during image construction.
- Fixed image digests replace floating tags.
- No `rm -rf src` or automatic registry push.
- The scanner's exit status must succeed, its JSON must contain the expected
  binary packages, and CVE-2023-44487 findings must be zero. The supplied
  `trivy ... | grep ... || echo ...` could incorrectly declare a failed scan clean.
- Build with `CGO_ENABLED=0`; the supplied external static-linker flags are not
  needed for this pure-Go binary.

## Aligned artifact: 4.0.2-kev.2

`artifacts/nfs-subdir-external-provisioner-4.0.2-kev.2.tar` is Linux/amd64.
It uses the already verified Go 1.26.9 / x/net v0.17.0 binary, replacing the old
binary in an export of the original image. All 2,009 other runtime entries are
preserved; inherited image configuration is preserved except the version label.
The archive has one filesystem layer, so the old binary is absent from all layers.

Original runtime image:
`registry.k8s.io/sig-storage/nfs-subdir-external-provisioner@sha256:374f80dde8bbd498b1083348dd076b8d8d9f9b35386a793f102d5deebe593626`.

**Runtime tradeoff:** the original image is Debian 9.13, marked end-of-life by
Trivy. Its scan has zero CVE-2023-44487 findings but 83 other findings:
33 high, 38 medium, 4 low, 8 unknown. Unsupported OS coverage means this is not
evidence that the old operating system is free of other vulnerabilities.
The earlier refreshed-runtime archive `4.0.2-kev.1` uses Debian 13 and has 80
other findings. Both archives remain local for review; neither was deployed.

SHA-256 of the aligned archive:
`74568fec755fdfb1d71b29e5dc3d129a17ee7f1b574c234b4c0b76b9d7c1e6c7`.

Evidence: `artifacts/trivy-kev2.json`, `artifacts/sbom-kev2.cdx.json`,
`artifacts/minimal-packaging.json`, and the earlier binary build metadata.
OpenShift/EFS integration tests still require the target test cluster.

For a Linux Podman rebuild, follow `KEV-REMEDIATION.md` using `--squash-all`.
For daemon-free packaging, export the original image with crane, save its config,
then run `python scripts/package-minimal-image.py artifacts`. That script expects
`original-rootfs.tar`, `original-image-config.json`, and the rebuilt Linux binary
in the artifact directory. It does not extract archive paths to the host or push
an image to a registry.
