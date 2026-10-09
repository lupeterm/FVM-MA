#!/bin/bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
script="$project_dir/variants/gpu_benchmark.sh"
fixture_dir=$(mktemp -d)
trap 'rm -rf "$fixture_dir"' EXIT

workspace="$fixture_dir/workspace"
results="$fixture_dir/results.csv"
calls="$fixture_dir/calls.log"
launcher="$fixture_dir/fake-julia"
mkdir -p "$workspace"

make_case() {
    local size=$1
    local case_dir="$workspace/LDC-$size/case"
    mkdir -p "$case_dir/constant/polyMesh" "$case_dir/system"
    printf 'hex (0 1 2 3 4 5 6 7) (%s %s %s) simpleGrading (1 1 1)\n' \
        "$size" "$size" "$size" > "$case_dir/system/blockMeshDict"
}

for size in 20 30 40 410; do
    make_case "$size"
done

cat > "$results" <<'CSV'
time_mean_ms,time_median_ms,gc_time_mean_ms,gc_time_median_ms,case,case_long,strategy,variant,language,precision,executor,use_kernelAbstractions,use_fusing,Threads,nnz,node
1,1,0,0,LDC-8000,LDC-8000,batchedFace,Fused,julia,float64,gpu,true,true,1,1,H100
1,1,0,0,LDC-8000,LDC-8000,faceBased,Fused,julia,float64,gpu,true,true,1,1,H200
1,1,0,0,LDC-27000,LDC-27000,batchedFace,Fused,julia,float64,gpu,true,true,1,1,H100
1,1,0,0,LDC-27000,LDC-27000,faceBased,Fused,julia,float64,gpu,true,true,1,1,H100
1,1,0,0,LDC-27000,LDC-27000,globalfaceBased,Fused,julia,float64,gpu,true,true,1,1,H100
1,1,0,0,LDC-27000,LDC-27000,cellBased,Fused,julia,float64,gpu,true,true,1,1,H100
1,1,0,0,LDC-64000,LDC-64000,batchedFace,Fused,julia,float64,gpu,true,true,1,1,H200
1,1,0,0,LDC-64000,LDC-64000,faceBased,Fused,julia,float64,gpu,true,true,1,1,H200
1,1,0,0,LDC-64000,LDC-64000,globalfaceBased,Fused,julia,float64,gpu,true,true,1,1,H200
1,1,0,0,LDC-64000,LDC-64000,cellBased,Fused,julia,float64,gpu,true,true,1,1,H200
CSV

cat > "$launcher" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >> "$CALLS_FILE"
SH
chmod +x "$launcher"

(
    cd "$project_dir/variants"
    CALLS_FILE="$calls" \
    WORKSPACE_ROOT="$workspace" \
    RESULTS_FILE="$results" \
    JULIA_LAUNCHER="$launcher" \
        bash "$script" H100 > "$fixture_dir/output.log"
)

cat > "$fixture_dir/expected.log" <<EOF
bench_variants_gpu.jl $workspace/LDC-20/case H100 faceBased globalfaceBased cellBased
bench_variants_gpu.jl $workspace/LDC-40/case H100 batchedFace faceBased globalfaceBased cellBased
EOF

if ! diff -u "$fixture_dir/expected.log" "$calls"; then
    echo "gpu_benchmark.sh did not invoke exactly the missing combinations" >&2
    exit 1
fi

if ! grep -Fq 'Skipping LDC-27000: all strategies already calculated for H100' "$fixture_dir/output.log"; then
    echo "complete case was not reported as skipped" >&2
    exit 1
fi

echo "gpu_benchmark.sh integration test passed"
