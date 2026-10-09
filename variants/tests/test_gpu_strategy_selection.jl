using Test

include("../gpu_benchmark_selection.jl")

@testset "GPU benchmark strategy selection" begin
    @test selected_strategies(String[]) == [
        "batchedFace",
        "faceBased",
        "globalfaceBased",
        "cellBased",
    ]
    @test selected_strategies(["faceBased", "cellBased"]) == [
        "faceBased",
        "cellBased",
    ]
    @test_throws ArgumentError selected_strategies(["notAStrategy"])
end
