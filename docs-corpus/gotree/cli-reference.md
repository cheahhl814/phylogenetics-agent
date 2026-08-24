gotree is a set of tools to handle phylogenetic trees in go.

Different usages are implemented: 
- Generating random trees
- Transforming trees (renaming tips, pruning/removing tips)
- Comparing trees (computing bootstrap supports, counting common edges)

Version: 

Usage:
  gotree [flags]
  gotree [command]

Available Commands:
  acr         Reconstructs most parsimonious ancestral characters
  annotate    Annotates internal branches of a tree with given data
  asr         Reconstructs most parsimonious ancestral sequences
  brlen       Modify branch lengths
  collapse    Collapse branches of input trees
  comment     Modify branch/node comments
  compare     Compare full trees, edges, or tips
  completion  Generate the autocompletion script for the specified shell
  compute     Computations such as consensus and supports
  cut         Cut the tree
  divide      Divide an input tree file into several tree files
  download    Download trees or images from servers
  draw        Draw trees
  generate    Generate random trees
  graft       Graft a tree t2 on a tree t1, at the position of a given tip
  help        Help about any command
  labels      Lists labels of all tree tips
  ltt         Lineage Through Time data
  matrix      Prints distance matrix associated to the input tree
  merge       Merges two rooted trees
  nni         Generates all NNI neighbors from a given tree
  prune       Remove tips of the input tree that are not in the compared tree
  reformat    Reformats an input tree file into different formats
  rename      Rename nodes/tips of the input tree
  repopulate  Re populate the tree with identical tips
  reroot      Reroot trees using an outgroup or at midpoint
  resolve     Resolve multifurcations by adding 0 length branches
  rotate      Rotates children of internal nodes
  rtt         Root To Tip regression
  sample      Takes a subsample of the set of trees from the input file
  shuffletips Shuffle tip names of an input tree
  stats       Print statistics about the tree
  subtree     Select a subtree from the input tree whose root has the given name
  support     Modify supports of branches
  unroot      Unroot input tree
  upload      Upload a tree to a given server
  version     Displays version of gotree

Flags:
      --format string   Input tree format (newick, nexus, phyloxml, or nextstrain) (default "newick")
  -h, --help            help for gotree
      --seed int        Random Seed: -1 = nano seconds since 1970/01/01 00:00:00 (default -1)
  -t, --threads int     Number of threads (Max=12) (default 1)

Use "gotree [command] --help" for more information about a command.


If you use the Gotree/Goalign toolkit, please cite:
Lemoine F, Gascuel O.
Gotree/Goalign: toolkit and Go API to facilitate the development of phylogenetic workflows.
NAR Genom Bioinform. 2021 Aug 11;3(3):lqab075.
doi: 10.1093/nargab/lqab075. PMID: 34396097; PMCID: PMC8356961.
