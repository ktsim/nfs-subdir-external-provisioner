# CVE-2023-44487 remediation for v4.0.2

Baseline: upstream tag `v4.0.2`, commit
`fab8b5623e7115adc01728d562e67a92ceca069a`
(annotated tag object `663b2d2631af9c64f19c9253ab85090902ba5232`).

This is a local custom build, version `4.0.2-kev.2`, not an official upstream release.
Application source, Kubernetes dependency versions, provisioner library, RBAC,
StorageClass definitions, environment variables, and entrypoint are unchanged.

## Patch scope

- Select `golang.org/x/net v0.17.0`, the fixed version for CVE-2023-44487.
- Its module graph selects companion dependencies `x/crypto v0.14.0`,
  `x/sys v0.13.0`, `x/text v0.13.0`, and `x/term v0.13.0`.
- Compile the static binary with Go 1.26.9, which includes the Go HTTP/2 fix.
- Use the exact original v4.0.2 runtime, pinned by digest; squash all layers.
- Keep the upstream build files intact; use `Dockerfile.kev` for this build.

References:

- https://github.com/advisories/GHSA-qppj-fm5r-hxr3
- https://github.com/golang/go/issues/63417
- https://pkg.go.dev/vuln/GO-2023-2102

## Rebuild on Linux with Podman or Docker

Run from the repository root on an amd64 Linux builder:

```sh
podman build --format docker --squash-all -f Dockerfile.kev \
  -t localhost/nfs-subdir-external-provisioner:4.0.2-kev.2 .
podman save --format docker-archive \
  -o artifacts/nfs-subdir-external-provisioner-4.0.2-kev.2.tar \
  localhost/nfs-subdir-external-provisioner:4.0.2-kev.2
```

The build runs `go test` for the application packages, builds with module changes
disabled, and prints embedded Go/module versions. This does not test EFS or
OpenShift integration. The image produced here targets linux/amd64.

## Scan and retain evidence

```sh
trivy image --input artifacts/nfs-subdir-external-provisioner-4.0.2-kev.2.tar \
  --scanners vuln --format json --output artifacts/trivy.json
trivy image --input artifacts/nfs-subdir-external-provisioner-4.0.2-kev.2.tar \
  --format cyclonedx --output artifacts/sbom.cdx.json
```

Require the exact image archive/digest to have no CVE-2023-44487 finding in your
approved scanner. Also review other findings: this minimal patch retains old
dependencies and does not promise that every other CVE has been resolved.
Retain the source diff, build/toolchain versions, base digests, image archive
SHA-256, SBOM, scan results, and integration test evidence.

## DPH OpenShift / AWS EFS validation

Before rollout, load and push the archive to your approved internal registry.
Use a new custom tag and record the registry digest; do not overwrite `v4.0.2`.
Change only the provisioner deployment image reference to the approved digest.
Keep its current service account, security context/SCC, environment variables,
NFS server/path, StorageClass, and reclaim settings.

In a test namespace using the existing StorageClass:

1. Confirm leader election and provisioner startup succeed with existing RBAC/SCC.
2. Create a disposable PVC and confirm it reaches `Bound` and creates the expected EFS subdirectory.
3. Mount it from a test pod and verify file creation, readback, permissions, and remount persistence.
4. Confirm existing PVCs can still mount and read/write through a disposable test workload.
5. Delete only the disposable PVC and verify the configured archive/delete/retain behavior.
6. Record pod events and provisioner logs, and repeat after a provisioner restart.

Production rollout and registry publication are not performed by the local build.
Keep the previous deployment image digest for rollback; preserve existing PV/PVCs.

## Earlier refreshed-runtime build (4.0.2-kev.1)

The Docker-archive image is saved in
`artifacts/nfs-subdir-external-provisioner-4.0.2-kev.1.tar`, tagged
`localhost/nfs-subdir-external-provisioner:4.0.2-kev.1`.

The Podman/WSL build stalled while C: was nearly full. The delivered image was
instead assembled locally using the Windows Go 1.26.9 toolchain to cross-compile
the same source for Linux/amd64, and Google's crane CLI to append the executable
to the pinned distroless image. No registry publication occurred. The Dockerfile
above remains an alternative Linux build recipe; it was not completed locally.

Executed build commands (Go caches were placed on D:):

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go test -p 2 -mod=readonly ./cmd/...
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -p 2 -mod=readonly -trimpath \
  -o artifacts/nfs-subdir-external-provisioner ./cmd/nfs-subdir-external-provisioner
go version -m artifacts/nfs-subdir-external-provisioner
python artifacts/make-layer.py
crane mutate \
  gcr.io/distroless/static@sha256:58133991db06659feaabe0f4e97a35cebf15ef4ea08f8a4c6d2ee5f75e4aa6a0 \
  --platform linux/amd64 --append artifacts/binary-layer.tar \
  --entrypoint /nfs-subdir-external-provisioner \
  --label org.opencontainers.image.version=4.0.2-kev.1 \
  --label org.opencontainers.image.revision=fab8b5623e7115adc01728d562e67a92ceca069a \
  --label org.opencontainers.image.source=https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner \
  --tag localhost/nfs-subdir-external-provisioner:4.0.2-kev.1 \
  --output artifacts/nfs-subdir-external-provisioner-4.0.2-kev.1.tar
```

Package check passed; this upstream application has no unit test files.
The binary metadata confirms Go 1.26.9, x/net v0.17.0, CGO disabled, and the
unchanged Kubernetes/provisioner library versions. Archive inspection confirms
Linux/amd64, the original entrypoint, executable permissions, and that the
packaged binary matches the compiled binary byte for byte.

Trivy 0.75.0 reports **zero CVE-2023-44487 findings** in this exact image.
It also reports **80 other findings**: 33 high, 38 medium, 4 low, 5 unknown.
These findings remain for your security review; the image is not claimed to be
free of all vulnerabilities. EFS/OpenShift runtime validation has not been run.

Archive SHA-256:
`d401739f4fcd329a1c7dcb42001f4978286114240d77e3158e36d30bda2fe758`.
This is the archive file checksum, not a registry image manifest digest.

Evidence: `artifacts/build-info.txt`, `artifacts/verification.json`,
`artifacts/trivy.json`, `artifacts/sbom.cdx.json`, and source patch files.

Load on your Linux image host using:

```sh
podman load -i artifacts/nfs-subdir-external-provisioner-4.0.2-kev.1.tar
# or: docker load -i artifacts/nfs-subdir-external-provisioner-4.0.2-kev.1.tar
```
