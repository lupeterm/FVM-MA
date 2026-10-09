include("gpu_benchmark_selection.jl")
include("gpu_face_variants.jl")
include("gpu_globalface_variants.jl")
include("gpu_cell_variants.jl")
# include("batched_variants.jl")
include("gpu_batched_variants.jl")
include("../operators.jl")

function benchmark_case(case::String, node::String, selected::Vector{String})
    suite = BenchmarkGroup()
    suite["gpu"] = BenchmarkGroup(["gpu"])
    meshInput = ProcessCase(Float64, case)
	numCells = meshInput.mesh.numCells
    nInternalFaces = meshInput.mesh.numInteriorFaces
	case = "LDC-$numCells"    
    suite["gpu"][case] = BenchmarkGroup(["gpu"])
    nthreads = Threads.nthreads()
    pde = Div{Float64,upwind{Float64}}(upwind{Float64}(), 1.0) + Laplace(1.0)

    if "batchedFace" in selected
        prep = getBatchedFaceBasedGpuInput(meshInput)
        suite["gpu"][case]["batchedFace"] = BenchmarkGroup(["gpu", "batchedFace"])
        suite["gpu"][case]["batchedFace"]["Fused"] = @benchmarkable FusedBatchedAssembly($prep..., $pde)
    end
    # suite["gpu"][case]["batchedFace"]["PrecalculatedWeightsUpwind"] = @benchmarkable PrecalculatedWeightsBatchedAssembly($prep..., $wUp)
    # suite["gpu"][case]["batchedFace"]["PrecalculatedWeightsCDF"] = @benchmarkable PrecalculatedWeightsBatchedAssembly($prep..., $wCdf)
    # suite["gpu"][case]["batchedFace"]["HardCodedUpwind"] = @benchmarkable HardcodedBatchedAssembly($prep..., $"upwind_f")
    # suite["gpu"][case]["batchedFace"]["HardCodedCDF"] = @benchmarkable HardcodedBatchedAssembly($prep..., $"CDF")
    # suite["gpu"][case]["batchedFace"]["DynamicCDF"] = @benchmarkable DynamicBatchedAssembly($prep..., $cdf_f)
    # suite["gpu"][case]["batchedFace"]["DynamicUpwind"] = @benchmarkable DynamicBatchedAssembly($prep..., $upwind_f)
    if "faceBased" in selected || "globalfaceBased" in selected
        input_facebased = faceInput(meshInput)
    end
    if "faceBased" in selected
        suite["gpu"][case]["faceBased"] = BenchmarkGroup(["gpu", "faceBased"])
        suite["gpu"][case]["faceBased"]["Fused"] = @benchmarkable gpu_fusedFaceBasedAssemblyRunner($input_facebased..., $pde)
    end
    # suite["gpu"][case]["faceBased"]["PrecalculatedWeightsUpwind"] = @benchmarkable gpu_PrecalculatedWeightsFaceBasedAssemblyRunner($input_facebased..., $wUp)
    # suite["gpu"][case]["faceBased"]["PrecalculatedWeightsCDF"] = @benchmarkable gpu_PrecalculatedWeightsFaceBasedAssemblyRunner($input_facebased..., $wCdf)
    # suite["gpu"][case]["faceBased"]["HardCodedUpwind"] = @benchmarkable gpu_HardcodedFaceBasedAssemblyRunner($input_facebased..., $"upwind_f")
    # suite["gpu"][case]["faceBased"]["HardCodedCDF"] = @benchmarkable gpu_HardcodedFaceBasedAssemblyRunner($input_facebased..., $"CDF")
    # suite["gpu"][case]["faceBased"]["DynamicCDF"] = @benchmarkable gpu_DynamicFaceBasedAssemblyRunner($input_facebased..., $cdf_f)
    # suite["gpu"][case]["faceBased"]["DynamicUpwind"] = @benchmarkable gpu_DynamicFaceBasedAssemblyRunner($input_facebased..., $upwind_f)
    
    if "globalfaceBased" in selected
        suite["gpu"][case]["globalfaceBased"] = BenchmarkGroup(["gpu", "globalfaceBased"])
        suite["gpu"][case]["globalfaceBased"]["Fused"] = @benchmarkable gpu_fusedGlobalFaceBasedAssemblyRunner($input_facebased..., $pde)
    end
    # suite["gpu"][case]["globalfaceBased"]["PrecalculatedWeightsUpwind"] = @benchmarkable gpu_PrecalculatedWeightsGlobalFaceBasedAssemblyRunner($input_facebased..., $wUp)
    # suite["gpu"][case]["globalfaceBased"]["PrecalculatedWeightsCDF"] = @benchmarkable gpu_PrecalculatedWeightsGlobalFaceBasedAssemblyRunner($input_facebased..., $wCdf)
    # suite["gpu"][case]["globalfaceBased"]["HardCodedUpwind"] = @benchmarkable gpu_HardcodedGlobalFaceBasedAssemblyRunner($input_facebased..., $"upwind_f")
    # suite["gpu"][case]["globalfaceBased"]["HardCodedCDF"] = @benchmarkable gpu_HardcodedGlobalFaceBasedAssemblyRunner($input_facebased..., $"CDF")
    # suite["gpu"][case]["globalfaceBased"]["DynamicCDF"] = @benchmarkable gpu_DynamicGlobalFaceBasedAssemblyRunner($input_facebased..., $cdf_f)
    # suite["gpu"][case]["globalfaceBased"]["DynamicUpwind"] = @benchmarkable gpu_DynamicGlobalFaceBasedAssemblyRunner($input_facebased..., $upwind_f)


    if "cellBased" in selected
        cellBasedPrep = getCellBasedGpuInput(meshInput)
        suite["gpu"][case]["cellBased"] = BenchmarkGroup(["gpu", "cellBased"])
        suite["gpu"][case]["cellBased"]["Fused"] = @benchmarkable FusedCell($cellBasedPrep, $pde)
    end
    # suite["gpu"][case]["cellBased"]["PrecalculatedWeightsUpwind"] = @benchmarkable PrecalculatedWeightsCell($cellBasedPrep, $wUp)
    # suite["gpu"][case]["cellBased"]["PrecalculatedWeightsCDF"] = @benchmarkable PrecalculatedWeightsCell($cellBasedPrep, $wCdf)
    # suite["gpu"][case]["cellBased"]["HardCodedUpwind"] = @benchmarkable HardcodedCell($cellBasedPrep, $"upwind_f")
    # suite["gpu"][case]["cellBased"]["HardCodedCDF"] = @benchmarkable HardcodedCell($cellBasedPrep, $"CDF")
    # suite["gpu"][case]["cellBased"]["DynamicCDF"] = @benchmarkable DynamicCell($cellBasedPrep, $cdf_f)
    # suite["gpu"][case]["cellBased"]["DynamicUpwind"] = @benchmarkable DynamicCell($cellBasedPrep, $upwind_f)
    results = run(suite, verbose=true)
    processResults(results, "standalone-gpu.csv", Float64, numCells + 2*nInternalFaces)
    
end
struct Result
    time_mean_ms::Float64
    time_median_ms::Float64
    gc_time_mean_ms::Float64
    gc_time_median_ms::Float64
    case_short::String
    case_long::String
    strategy::String
    variant::String
    language::String
end

ResultToCsvRow(r::Result, cpu::Bool, precision::String, use_kernelAbstractions::Bool, use_fusing::Bool,nnz::Int) = "$(r.time_mean_ms),$(r.time_median_ms),$(r.gc_time_mean_ms),$(r.gc_time_median_ms),$(r.case_short),$(r.case_long),$(r.strategy),$(r.variant),$(r.language),$precision,$(ifelse(cpu, "cpu", "gpu" )),$use_kernelAbstractions,$use_fusing,$(Threads.nthreads()),$nnz,$(ARGS[2])\n"

function processResults(results::BenchmarkGroup, file::String, T, nnz)
    if !isfile(file)
		open("$(file)", "a") do io
	        write(io, join("time_mean_ms,time_median_ms,gc_time_mean_ms,gc_time_median_ms,case,case_long,strategy,variant,language,precision,executor,use_kernelAbstractions,use_fusing,Threads,nnz,node\n"))
	    end
	end
    for (cpu_gpu, perDataset) in results
        println("[CPU, GPU]: $cpu_gpu ")
        for (case, perStrategy) in perDataset
            println("\t[CASE]: $case ")
            for (strategy, variant) in perStrategy
                println("\t\t[STRATEGY]: $strategy ")
                for (variation, values) in variant
                    r = Result(
                        mean(values).time / 1e6,
                        median(values).time / 1e6,
                        mean(values).gctime / 1e6,
                        median(values).gctime / 1e6,
                        case,
                        case,
                        strategy,
                        variation,
                        "julia"
                    )
                    println("\t\t\t[VARIATION]: $variation ")
                    println("\t\t\t --> time_mean_ms,time_median_ms,gc_time_mean_ms,gc_time_median_ms,case,case_long,strategy,variant,language,precision,executor,use_kernelAbstractions,use_fusing,Threads,nnz")
                    println("\t\t\t --> $(ResultToCsvRow(r, cpu_gpu == "cpu", "float64", contains(variation,"Abstract") || contains(strategy, "Abstract"), contains(variation, "Fused"), nnz))\n")
                    open("$(file)", "a") do io
                        write(io, ResultToCsvRow(r, cpu_gpu == "cpu", "float64", contains(variation, "Abstract") || true, true, nnz))
                    end
                end
            end
        end
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    case = ARGS[1]
    node = ARGS[2]
    requested = length(ARGS) > 2 ? ARGS[3:end] : String[]
    benchmark_case(case, node, selected_strategies(requested))
end
