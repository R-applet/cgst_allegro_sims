# Production defaults shared by the Part 2/3 submit scripts (sourced, not executed; tests set dt themselves). Override per job via the environment,
# e.g. sbatch --export=ALL,DT=0.001 ...  Change a value here only together with the test that justifies it.
#   DT  timestep (ps). 2 fs passes NVE energy conservation in the hottest, most C-rich state (tests/RESULTS.md, 1c).
#       Every run in a chain (melt-quench -> ramp/anneal, and anneal resumes) must use the same DT.
DT=${DT:-0.002}
