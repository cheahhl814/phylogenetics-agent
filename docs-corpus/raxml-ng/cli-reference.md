
RAxML-NG v. 2.0.2 released on 29.05.2026 by The Exelixis Lab.
Developed by: Oleksiy M. Kozlov and Alexandros Stamatakis.
Contributors: Diego Darriba, Tomas Flouri, Benoit Morel, Sarah Lutteropp, Ben Bettisworth,
              Julia Haag, Anastasis Togkousidis, Julius Wiegert, Christoph Stelz.
Latest version: https://github.com/amkozlov/raxml-ng
Questions/problems/suggestions? Please visit: https://groups.google.com/forum/#!forum/raxml

System: AMD Ryzen 5 7430U with Radeon Graphics, 6 cores, 14 GB RAM

Usage: raxml-ng [OPTIONS]

Commands (mutually exclusive):
  --help                                     display help information
  --version                                  display version information
  --evaluate                                 evaluate the likelihood of a tree (with model+brlen optimization)
  --search                                   ML tree search (default: use adaptive heuristic)
  --bootstrap                                bootstrapping (default: use bootstopping to auto-detect #replicates)
  --all                                      all-in-one (ML search + bootstrapping)
  --support                                  compute bipartition support for a given reference tree (e.g., best ML tree)
                                             and a set of replicate trees (e.g., from a bootstrap analysis)
  --bsconverge                               test for bootstrapping convergence using autoMRE criterion
  --bsmsa                                    generate bootstrap replicate MSAs
  --terrace                                  check whether a tree lies on a phylogenetic terrace 
  --check                                    check alignment correctness and remove empty columns/rows
  --parse                                    parse alignment, compress patterns and create binary MSA file
  --start                                    generate parsimony/random starting trees and exit
  --rfdist                                   compute pair-wise Robinson-Foulds (RF) distances between trees
  --consense [ STRICT | MR | MR<n> | MRE ]   build strict, majority-rule (MR) or extended MR (MRE) consensus tree (default: MR)
                                             eg: --consense MR75 --tree bsrep.nw
  --ancestral                                ancestral state reconstruction at all inner nodes
  --mutmap                                   map mutations to the tree branches
  --sitelh                                   print per-site log-likelihood values
  --pythia                                   compute and print Pythia MSA difficulty score
  --moose [ OPTIONS ]                        select best-fit MOdel Of Sequence Evolution (OPTIONS: see below)

Command shortcuts (mutually exclusive):
  --search1                                  Alias for: --search --tree pars{1}
  --fast                                     Alias for: --search --tree pars{1} --opt-topology simplified --stop-rule kh-mult
  --allfast                                  Alias for: --all --tree pars{1} --opt-topology simplified --stop-rule kh-mult --bs-metric ebg
  --loglh                                    Alias for: --evaluate --opt-model off --opt-branches off --nofiles --log result
  --rf                                       Alias for: --rfdist --nofiles --log result
  --pt                                       Alias for: --pythia --nofiles --log result
  --sh [ REPS ]                              Alias for: --all --opt-topology nni --bs-metric sh [ --sh-reps REPS ]
  --ebg                                      Alias for: --all --bs-metric ebg --opt-topology off
  --gcf [ REF_TREE ]                         Alias for: --support --bs-metric gcf [ --tree REF_TREE ] 

Input and output options:
  --tree            rand{N} | pars{N} |      starting tree: rand(om), pars(imony) or user-specified (newick file)
                    FILE | auto              N = number of trees (default: auto-detect based on MSA difficulty)
  --msa             FILE                     alignment file
  --msa-format      VALUE                    alignment file format: FASTA, PHYLIP, CATG or AUTO-detect (default)
  --data-type       VALUE                    data type: DNA, AA, BIN(ary) or AUTO-detect (default)
  --tree-constraint FILE                     constraint tree
  --prefix          STRING                   prefix for output files (default: MSA file name)
  --log             VALUE                    log verbosity: ERROR,WARNING,RESULT,INFO,PROGRESS,DEBUG (default: PROGRESS)
  --redo                                     overwrite existing result files and ignore checkpoints (default: OFF)
  --nofiles                                  do not create any output files, print results to the terminal only
  --precision       VALUE                    number of decimal places to print (default: 6)
  --outgroup        o1,o2,..,oN              comma-separated list of outgroup taxon names (it's just a drawing option!)
  --site-weights    FILE                     file with MSA column weights (positive integers only!)  

General options:
  --seed         VALUE                       seed for pseudo-random number generator (default: current time)
  --pat-comp     on | off                    alignment pattern compression (default: ON)
  --tip-inner    on | off                    tip-inner case optimization (default: OFF)
  --site-repeats on | off                    use site repeats optimization, 10%-60% faster than tip-inner (default: ON)
  --threads      VALUE                       number of parallel threads to use (default: auto{6})
  --workers      VALUE                       number of tree searches to run in parallel (default: auto)
  --simd         none | sse3 | avx | avx2    vector instruction set to use (default: auto-detect).
  --rate-scalers on | off                    use individual CLV scalers for each rate category (default: ON for >2000 taxa)
  --force        [ <CHECKS> ]                disable safety checks (please think twice!)

Model options:
  --model        <name>+G[n]+<Freqs> | FILE  model specification OR partition file
  --brlen        linked | scaled | unlinked  branch length linkage between partitions (default: scaled)
  --blmin        VALUE                       minimum branch length (default: 1e-6)
  --blmax        VALUE                       maximum branch length (default: 100)
  --blopt        nr_fast    | nr_safe        branch length optimization method (default: nr_fast)
                 nr_oldfast | nr_oldsafe     
  --opt-model    on | off                    ML optimization of all model parameters (default: ON)
  --opt-branches on | off                    ML optimization of all branch lengths (default: ON)
  --prob-msa     on | off                    use probabilistic alignment (works with CATG and VCF)
  --lh-epsilon   VALUE                       log-likelihood epsilon for optimization/tree search (default: 10)
  --opt-freerate bfgs | em-bfgs | em-brent   optimization method for FreeRates (default: auto)

Model selection options:
  --moose-options OPT=VAL/OPT=VAL/...        list of MOdel Optimization and SElection options separated by '/'
      criterion=AIC | AICc | BIC             information criterion to use for model selection (default: BIC)
      ic-delta=VALUE                         significance threshold for IC score difference (default: 10.0)
      freerate-categories=n[-m]              test FreeRate models with n categories (optionally up to and including m)
      rhas=VAL1,VAL2,...                     list of rate heterogeneity across sites (RHAS) models (default: R,I+R,E,I,G,I+G)
      substitution-models=VAL1,VAL2,...      list of substitutions models (default: all supported)
      heuristics=VAL1,VAL2,... | off         heuristics to skip models (default: rhas,freerate)

Topology search options:
  --opt-topology        classic | adaptive   topology optimization method (default: adaptive)
                        simple  | nni        
                        rbs | off            
  --adaptive            [ on | off | start ] adaptive ML tree search (start = starting trees only)
  --spr-radius          VALUE                SPR re-insertion radius for fast iterations (default: AUTO)
  --spr-cutoff          VALUE | off          relative LH cutoff for descending into subtrees (default: 1.0)
  --lh-epsilon-triplet  VALUE                log-likelihood epsilon for branch length triplet optimization (default: 1000)
  --stop-rule           sn-rell | sn-normal  stopping criterion for SPR rounds (default: OFF)
                        kh | kh-mult | off   

Bootstrapping and branch support options:
  --bs-trees     N | fbp{N1},sh{N2},...      number of bootstrap replicates N, can be global or per-metric (see below)
  --bs-trees     autoMRE{N}                  use MRE-based bootstrap convergence criterion, up to N replicates (default: 1000)
  --bs-trees     FILE                        Newick file containing set of bootstrap replicate trees (with --support)
  --bs-cutoff    VALUE                       cutoff threshold for the MRE-based bootstopping criteria (default: 0.03)
  --bs-metric    fbp | rbs |                 branch support metric: fbp = Felsenstein bootstrap (default), rbs = Rapid bootstrap
                 ebg | tbe | sh              ebg = Educated bootstrap guesser, tbe = Transfer bootstrap estimate, sh = SH-like aLRT
                 ps  | pbs |                 ps = Parsimony support, pbs = Parsimony bootstrap support
                 ic1 | ica                   ic1 = Internode certainty (most prevalent), ica = Internode certainty (all)
                 gcf                         gcf = Gene concordance factor
  --bs-write-msa on | off                    write all bootstrap alignments (default: OFF)

SH-like test options:
  --sh-reps      VALUE                       number of bootstrap replicates for SH-aLRT test (default: 1000)
  --sh-epsilon   VALUE                       log-likelihood epsilon for SH-aLRT test (default: 0.1)

EXAMPLES:
  1. Perform tree inference on DNA alignment 
     (select best-fit model, adaptive search heuristic based on MSA difficulty):

     ./raxml-ng --msa testDNA.fa --model DNA


  2. Perform an all-in-one analysis (ML tree search + non-parametric bootstrap) 
     (10 randomized parsimony starting trees, fixed empirical substitution matrix (LG),
      empirical aminoacid frequencies from alignment, 8 discrete GAMMA categories,
      200 bootstrap replicates):

     ./raxml-ng --all --msa testAA.fa --model LG+G8+F --tree pars{10} --bs-trees 200


  3. Optimize branch lengths and free model parameters on a fixed topology
     (using multiple partitions with proportional branch lengths)

     ./raxml-ng --evaluate --msa testAA.fa --model partitions.txt --tree test.tree --brlen scaled

