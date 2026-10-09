const GPU_BENCHMARK_STRATEGIES = [
    "batchedFace",
    "faceBased",
    "globalfaceBased",
    "cellBased",
]

function selected_strategies(requested::Vector{String})
    isempty(requested) && return copy(GPU_BENCHMARK_STRATEGIES)

    unknown = setdiff(requested, GPU_BENCHMARK_STRATEGIES)
    isempty(unknown) || throw(ArgumentError(
        "unknown GPU benchmark strategy: $(join(unknown, ", "))",
    ))
    return requested
end
