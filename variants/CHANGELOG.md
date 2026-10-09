# Changelog

## 2026-08-08

### Fixed

- Fixed the out-of-bounds GPU access in `FusedBatchedAssembly`'s boundary
  kernel. Greedy edge coloring produces several internal-face batches followed
  by the boundary batch, but the boundary kernel was incorrectly passed
  `batches[2]`. For the reproduced 1,000-cell case, that selected a 500-face
  internal color batch while launching 600 boundary-face threads, so threads
  501 through 600 indexed beyond the selected batch's face arrays.
- The boundary kernel now receives `batches[end]`, the actual 600-face boundary
  batch, and launches over `length(bFaceMapping)`, matching both the boundary
  batch and the established boundary-kernel pattern. The unused
  internal-face-count kernel argument was removed.

### Verification

- Reproduced the original failure with `bash gpu_benchmark.sh` on an NVIDIA
  H200 NVL: CUDA reported a `BoundsError` during the fused batched boundary
  kernel for the 1,000-cell case.
- Re-ran `bash gpu_benchmark.sh` after the fix to verify the fused batched
  assembly completes without the out-of-bounds error.
