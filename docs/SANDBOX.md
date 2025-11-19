# Plugin sandboxing design (prototype)

This document outlines options and a proposed prototype path for sandboxing plugins at the OS level. It focuses on Linux and covers unprivileged namespaces (unshare), chroot/jail approaches, seccomp, and container-based isolation. The goal is to provide actionable prototypes and a migration path for stronger plugin isolation (P3 work in the roadmap).

## Goals
- Run untrusted or third-party plugin code with least privilege.
- Limit filesystem and kernel surface accessible to plugins.
- Capture stdout/stderr and enforce timeouts/resource limits.
- Make sandboxing opt-in and incremental (per-plugin) with clear diagnostics.

## Constraints
- CI and contributor workflows must remain practical: requiring root for day-to-day development is unacceptable.
- Some sandbox features (chroot, seccomp) may require additional capabilities or privileged runners.
- Aim for a prototype that works on modern Linux kernels without extra system packages where possible.

## Options considered

### 1) Unprivileged user namespaces (unshare + map-root-user)
- Mechanism: use `unshare` (util-linux) or clone(CLONE_NEWUSER|...) to create a user namespace, then mount/namespace resources and drop capabilities.
- Pros: Can be done unprivileged on kernels that allow userns (many distributions do). Provides isolation of mount/pid/net namespaces.
- Cons: Distribution/VMs may disable userns for security; mapping root inside the namespace still gives root inside the namespace which may be dangerous without further restrictions.

### 2) Chroot / pivot_root
- Mechanism: set up a minimal chroot tree and run plugin inside it.
- Pros: Simple conceptually.
- Cons: Requires privileged setup (mounting, creating minimal /proc, /dev), not sufficient alone for security.

### 3) Seccomp filters (libseccomp)
- Mechanism: restrict syscalls available to plugin process via seccomp-BPF.
- Pros: Powerful syscall-level hardening.
- Cons: Complex to craft safe filter; requires libseccomp and careful testing. Hard to implement portably from pure Python without extra native deps.

### 4) Containers (podman/docker)
- Mechanism: run plugin inside a container with limited capabilities and seccomp profile.
- Pros: Robust isolation, well-understood tooling, easy to apply limited capabilities and filesystem layers.
- Cons: Requires container runtime available (not always desirable on developer machines/CI) and more complex orchestration.

## Prototype recommendation (incremental)

**Phase A (low friction, experiment):** implement subprocess + user namespace via `unshare --user --map-root-user` when available. Provide a fallback to the existing subprocess runner when userns isn't available. This allows experimentation without requiring privileged CI.

**Phase B (harden):** integrate seccomp profiles via a small native helper or use a sandboxing tool (e.g., Firejail, bubblewrap) where available.

**Phase C (enterprise/hard):** provide container modes (podman/docker) for highest isolation with documented CI requirements and optional GitHub Actions self-hosted runners.

## Security considerations
- Never enable sandboxing by default for all plugins; make it opt-in per-plugin or via an explicit config flag.
- Record and surface stderr/stdout from sandboxed processes for debugging.
- Apply strict timeouts and resource limits (RLIMITS) to avoid runaway processes.
- Audit any helper native code (C bindings) and avoid suid binaries.

## Testing plan
- Unit tests for the subprocess runner must verify expected behavior with and without userns.
- Integration tests: run plugin inside sandbox with mounted tmpfs and assert no writes outside allowed paths.
- CI: run prototype tests on a matrix; document kernel features required (userns enabled) and gracefully skip tests when not available.

## Rollout plan
- Merge the prototype scripts and docs behind an opt-in flag.
- Add per-plugin opt-in field `PLUGIN_INFO['isolate'] = 'sandbox'` (string indicating desired level: 'subprocess'|'userns'|'container').
- Add CI jobs to validate sandbox behavior on runners that support the required kernel features.

## References
- unshare(1) and util-linux
- bubblewrap (https://github.com/containers/bubblewrap)
- libseccomp (https://github.com/seccomp/libseccomp)

## Next steps (actionable)
- Prototype: add `scripts/prototype_sandbox.sh` that attempts to run the plugin worker in `unshare --user --map-root-user` and sets up a minimal /proc mount. Falls back if unavailable.
- Add tests exercising the prototype on dev machines where userns is available.
- Document required kernel features and CI implications in this doc.
