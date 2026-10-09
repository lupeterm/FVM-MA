#!/bin/bash
set -u

node=${1:-}
if [ -z "$node" ]; then
	echo "Usage: $0 NODE" >&2
	exit 2
fi

workspace_root=${WORKSPACE_ROOT:-/storage/home/lupeterm/nobackup/julia/workspace}
results=${RESULTS_FILE:-standalone-gpu.csv}
julia_launcher=${JULIA_LAUNCHER:-$HOME/.juliaup/bin/julialauncher}
strategies=(batchedFace faceBased globalfaceBased cellBased)
total=$((30 * ${#strategies[@]}))
finished=0

if [ -e "$results" ] && [ ! -r "$results" ]; then
	echo "$results is not readable." >&2
	exit 2
fi

has_result() {
	local case_name=$1
	local strategy=$2

	[ -f "$results" ] || return 1
	awk -F, -v case_name="$case_name" -v strategy="$strategy" -v node="$node" '
		{
			row_node = $16
			sub(/\r$/, "", row_node)
		}
		$5 == case_name && $7 == strategy && $8 == "Fused" && row_node == node {
			found = 1
			exit
		}
		END { exit !found }
	' "$results"
}

for dir in "$workspace_root"/*
do
	if [ ! -d "$dir/case/constant/polyMesh" ]; then
		echo "$dir/case/constant/polyMesh does not exist."
		continue
	fi

	size=$(sed -nE 's/.*\(([0-9]{2,3}) [0-9]{2,3} [0-9]{2,3}\).*/\1/p' \
		"$dir/case/system/blockMeshDict" | head -n 1)
	if [ -z "$size" ]; then
		echo "Could not determine LDC size from $dir/case/system/blockMeshDict" >&2
		continue
	fi

	if ! { [ "$size" -ge 10 ] && [ "$size" -le 200 ] && [ $((size % 10)) -eq 0 ]; } &&
	   ! { [ "$size" -ge 220 ] && [ "$size" -le 400 ] && [ $((size % 20)) -eq 0 ]; }; then
		echo "Skipping size $size: outside expected LDC range"
		continue
	fi

	ncells=$((size * size * size))
	case_name="LDC-$ncells"
	missing=()
	for strategy in "${strategies[@]}"; do
		if has_result "$case_name" "$strategy"; then
			finished=$((finished + 1))
		else
			missing+=("$strategy")
		fi
	done

	if [ ${#missing[@]} -eq 0 ]; then
		echo "Skipping $case_name: all strategies already calculated for $node"
		continue
	fi

	echo "[$finished / $total] Benchmarking $case_name on $node; missing: ${missing[*]}"
	"$julia_launcher" bench_variants_gpu.jl "$dir/case" "$node" "${missing[@]}"
	status=$?
	if [ "$status" -ne 0 ]; then
		echo "Benchmark failed for $case_name with exit code $status" >&2
		exit "$status"
	fi
	finished=$((finished + ${#missing[@]}))
done

echo "Done with $finished/$total benchmark combinations."
