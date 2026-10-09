#!/bin/bash
numcases=30
total=$(($numcases*8))
finished=0
# for dir in /storage/home/lupeterm/nobackup/julia/workspace/*
# do
# 	echo "[$finished / $total] Benchmarking ${dir}"   
# 	if [ ! -d "$dir/case/constant/polyMesh" ]; then
# 			echo "$dir/case/constant/polyMesh does not exist."
# 			continue
# 	fi
# 	ncells=$(sed -nE 's/.* ([0-9]{2,3}).*/\1/p' $dir/case/system/blockMeshDict)
# 	ncells=$((ncells * ncells * ncells))
# 	for nthreads in 2 4 8 16 32 64 128
#   	do
# 	# nthreads=128
# 	if grep -Eq "LDC-$ncells,.+,$nthreads,H200$" variations_cpu_polyester_pinnedthreads.csv
# 	then
# 		echo "[$finished / $total] already calculated for $ncells cells and $nthreads threads"
# 		# finished=$(($finished+1))
# 		continue
# 		# echo "[$finished / $total] not yet calculated for $ncells cells and $nthreads"
# 	fi
# 	finished=$(($finished+1))
#   	done
# done
# echo "##"
# echo "##"
# echo "##"
for dir in /storage/home/lupeterm/nobackup/julia/workspace/*
do
	echo "[$finished / $total] Benchmarking ${dir}"   
	if [ ! -d "$dir/case/constant/polyMesh" ]; then
			echo "$dir/case/constant/polyMesh does not exist."
			continue
	fi
	ncells=$(sed -nE 's/.* ([0-9]{2,3}).*/\1/p' $dir/case/system/blockMeshDict)
	ncells=$((ncells * ncells * ncells))
	for todo in  8000 125000 216000 1728000 2197000 2744000 4913000 5832000 6859000 10648000 13824000 17576000 46656000
	do 
		if [ $ncells -gt $todo ]; then
			continue	
		fi
		if [ $ncells -lt $todo ]; then
			continue	
		fi
		~/.juliaup/bin/julialauncher bench_variants.jl $dir/case

	done
	# for nthreads in 1  2 4 8 16 32 64 128
  	# do
	# nthreads=128
	# if grep -Eq "LDC-$ncells,.+,$nthreads,H200$" standalone-fused.csv
	# then
	# 	# echo "[$finished / $total] already calculated for $ncells cells and $nthreads threads"
	# 	# finished=$(($finished+1))
	# 	continue
	# else
	# 	echo "[$finished / $total] not yet calculated for $ncells cells and $nthreads"
	# fi
	
	# ~/.juliaup/bin/julialauncher -t $nthreads bench_variants.jl $dir/case
	# ~/.juliaup/bin/julialauncher bench_variants.jl $dir/case
	finished=$(($finished+1))
  	# done
done
echo "Done with $finished/$total benchmark runs."

