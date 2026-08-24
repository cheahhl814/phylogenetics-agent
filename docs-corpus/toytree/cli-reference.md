A minimalist Python package for representing tree objects, performing
operations on trees, and performing tree visualization.

Toytree's primary use if for visualizing and manipulating tree data
structures. It includes a number of additional subpackages for working
with trees as data, or data on trees. All subpackages make use only of
standard Python data science libs (e.g., numpy, scipy, pandas).


Help on function tree in module toytree.io.src.treeio:

tree(
    data: Union[str, Path, Url],
    feature_prefix: str = '&',
    feature_delim: str = ',',
    feature_assignment: str = '=',
    internal_labels: Optional[str] = None
) -> ToyTree
    Return a ToyTree parsed from variable input types and formats.

    Returns a :class:`ToyTree` object from a variety of optional
    input types, including a newick or nexus string, or a filepath or
    Url to a file containing a newick or nexus string. This function
    will try to auto-detect whether internal node labels are names
    or support values. If the newick string contains additional
    metadata as NHX annotations these will be parsed and stored as Node
    features.

    Parameters
    ----------
    data: Union[str, Path, Url]
        One of several allowed input types containing tree data. The
        str type can be a newick string or valid file path; the Path
        type must be a pathlib.Path object; the Url type is any string
        starting with http, from which str data will be fetched.
    feature_prefix: str
        If NHX meta data is present in the newick string enter the
        common prefix contained in each set of square brackets.
        Common options are "", "&", or "&&NHX:". Default="&".
    feature_delim: str
        If NHX meta data is present in the newick string enter the
        delimiter used to separate key-value pairs. Default=",".
    feature_assignment: str
        If NHX meta data is present in the newick string enter the
        assignment operator between key-value pairs. Default="=".
    internal_labels: str or None
        Labels next to internal nodes are often interchangeably used to
        record node names or support values. Enter "name", "support",
        or a different feature name to assign the values to. Default
        is None which mean toytree will infer as 'name' vs 'support'
        based on whether values are str or numeric type.

    Examples
    --------
    >>> tree = toytree.tree("((a,b),c);")
    >>> tree = toytree.tree("((a:10,b:20)A:100,c:30);")
    >>> tree = toytree.tree("/tmp/test.nex")
    >>> tree = toytree.tree("https://eaton-lab.org/data/Cyathophora.tre")


Help on function draw in module toytree.core.tree:

draw(
    self,
    tree_style: Optional[str] = None,
    height: int = None,
    width: int = None,
    axes: Cartesian = None,
    layout: str = None,
    tip_labels: Union[bool, Sequence] = None,
    tip_labels_colors: Union[Color, Sequence[Color]] = None,
    tip_labels_angles: Union[float, Sequence[float]] = None,
    tip_labels_style: Dict[str, Any] = None,
    tip_labels_align: bool = None,
    node_mask: Union[bool, Sequence[bool]] = None,
    node_labels: Union[bool, Sequence[str]] = None,
    node_labels_style: Dict[str, Any] = None,
    node_sizes: Union[int, Sequence[int]] = None,
    node_colors: Union[str, Sequence[str]] = None,
    node_style: Dict[str, Any] = None,
    node_hover: bool = None,
    node_markers: Sequence[str] = None,
    node_as_edge_data: bool = False,
    edge_colors: Union[str, Sequence[str]] = None,
    edge_widths: float = None,
    edge_type: str = None,
    edge_style: Dict[str, Any] = None,
    edge_align_style: Dict[str, Any] = None,
    edge_markers: Sequence[str] = None,
    edge_labels: Union[bool, Sequence[str]] = None,
    use_edge_lengths: bool = None,
    scale_bar: bool = None,
    padding: float = None,
    xbaseline: float = None,
    ybaseline: float = None,
    admixture_edges: List[Tuple[int, int]] = None,
    shrink: float = None,
    fixed_order: Sequence[str] = None,
    fixed_position: Sequence[float] = None,
    label: Optional[str] = None,
    **kwargs
) -> Tuple[Canvas, Cartesian, ToyTreeMark]
    Return a drawing of the tree as a Toyplot figure.

    Drawings are returned as Tuple[Canvas, Cartesian, ToytreeMark]
    following the style of the toyplot plotting library and will
    render as html figures automatically in jupyter notebook.
    The Canvas can be saved to file in a number of formats using
    toyplot. The Cartesian axes object can be used to position
    multiple Marks onto the same cartesian coordinates, and to
    style axes ticks and labels (see docs). The Mark object can
    be further modified to edit or access style args.

    Parameters
    ----------
    tree_style: str or None
        Select a builtin base TreeStyle on top of which to add other
        style modifications. Options include "n", "c", "p", "o",
        "r", "m", "d"; you can alo create your own (see docs).
        Using a tree_style overrides any `ToyTree.style` dict.
    ts: str or None
        A shorter alias that can be used for `tree_style`.
    height: int or None
        If None the plot height is auto-sized. If 'axes' arg is
        used tree is drawn on an existing Axes and this arg is
        ignored. Else, this sets height of the Canvas in px units.
    width: int
        If None the plot width is auto-sized. If 'axes' arg is
        used tree is drawn on an existing Axes and this arg is
        ignored. Else, this sets width of the Canvas in px units.
    axes: toyplot.coordinates.Cartesian
        A toyplot Cartesian axes object. If provided, tree is drawn
        on it. If not provided then a new Canvas and Cartesian
        axes are created and returned with the tree Mark added to
        it. See documentation for details on how this option is
        used to create composite drawings combining tree plots
        with other data plots (e.g., scatterplots, barplots).
    layout: str or None
        Layout defines the direction parent-child relationships are
        drawn. Options are 'r' 'l', 'u', 'd' for 'right', 'left',
        'up', or 'down' respectively. 'c' draws circular trees from
        angle 0-360 degrees, or cX-Y draws circular trees on an arc
        from X degrees to Y degrees. Finally, any other entry, such
        as None, draws an 'unrooted' layout. Default='r'.
    tip_labels: bool or Sequence[str]
        If True, tip labels ('name' features on tip Nodes) are
        added to the plot; if False, no tip labels are added. If a
        list of tip labels is provided it must be the same len as
        ntips and is applied in Node idx order (0-ntips).
    tip_labels_colors: Color or Sequence[Color] or (feature, colormap)
        A valid toyplot Color, Sequence[Color] of len=ntips, or
        tuple of (feature, colormap) to map colors to tip labels.
    tip_labels_style: Dict[str, str]
        A dictionary of CSS style arguments to apply to text
        tip labels. See tree.style for options.
    tip_labels_angles: int, Sequence[int], or None
        None will set angles based on layout method.
    tip_labels_align: bool
        If True tip names will be aligned and dashed edges will
        drawn to extend from tree edges to the tip names.
    node_mask: bool or Sequence[bool]
        Masks nodes (size, color, shape, label) if True, shows
        nodes if False. An iterable can be entered to selectively
        hide some nodes. The convenience function .get_node_mask()
        can be used to generate mask arrays. Default options
        vary among tree styles, but usually hide tip nodes.
    node_labels: bool, str, or Sequence[str]
        Labels associated with nodes. True shows node idx labels,
        False hides node labels (sets to ""). A string or
        iterable of strings assigns labels to nodes 0-nnodes.
        An iterable of string values can be generated from node
        features using .get_node_data() or .get_node_labels(),
        the latter includes string formatting options.
    node_sizes: int or Sequence[int]
        Size of node markers can be set as an integer or Iterable
        of integers in node order 0-nnodes. Node size 0 is hidden.
        The node_mask argument sets nodes to size 0 when masked,
        and overrides this argument.
    node_colors: str or Sequence[str]
        Color of node markers can be a single color or Iterable
        of colors in node order 0-nnodes. Any valid toyplot color
        (str, rgb array, rgba array, hex, etc) is accepted. See
        the toyplot.color module. The default color palette is
        accessible from toytree.colors. If all nodes will be set
        to the same color it is more efficient to use the
        node_style dictionary (node_style={"fill": 'red'}). If
        used, node_colors overrides 'fill' in node_style.
    node_style: Dict[str, str]
        A dict of valid CSS styles to apply to node markers, such
        as 'fill', 'stroke'. See tree.style for options.
    node_hover: True, False, or Sequence[str]
        Default is True in which case node hover will show the
        node values. If False then no hover is shown. If a list or
        dict is provided (which should be in node order) then the
        values will be shown in order. If a dict then labels can
        be provided as well.
    node_markers: str or Sequence[str]
        The shape of node markers: 'o'=circle, 's'=square. See
        toyplot documentation for all available options:
        https://toyplot.readthedocs.io/en/stable/markers.html
    node_as_edge_data: bool
        If True then node_markers and node_labels are instead
        plotted as edge_markers and edge_labels. For more fine
        control see `toytree.annotate`.
    edge_colors: str or Sequence[str]
        A color or collection of colors nnodes in length to apply
        to edges in node idx order.
    edge_widths: float or Sequence[float]
        A width arg in px units, or collection of widths to apply
        to edges in node idx order.
    edge_type: str
        Edges can be phylogram ('p') or cladogram ('c') type.
    edge_style: Dict[str, Any]
        A dictionary of valid CSS style args to apply to edge
        lines. See tree.style for available options.
    edge_align_style: Dict[str, Any]
        A dictionary of valid CSS style args to apply to aligned
        edge lines. See tree.style for available options.
    use_edge_lengths: bool
        If True edge lengths ('dist' features of TreeNodes) are
        represented in drawings. If False all terminal edges are
        extended to align tips at 0.
    scale_bar: bool
        If True then the axis corresponding to the height of the
        tree will be set to visible and tick marks will be auto-
        generated to span from time=0 to root height. The style
        of the axes can be further modified from the axes object
        after the draw function is called.
    padding: float
        Padding space between the drawing and the visible axes. This
        is a setting of the Cartesian axes and can be modified more
        after plotting. Default=20 (px).
    xbaseline: float
        Shift the position of the tree along x-axis.
    ybaseline: float
        Shift the position of the tree along y-axis.
    admixture_edges: Tuple, List[Tuple]
        Admixture edges add colored edges to the plot in the
        style of the 'edge_align_style'. These will be drawn
        from (source, dest, height, width, color). Example:
        `>>> [(4, 3, 50000, 3, 'red')]`.
    fixed_order: Sequence[str]
        An Iterable of tip labels in the order they should be
        plotted. The default is the node names in idx order
        0-ntips. These nodes will be plotted on the coordinates
        0-ntips on either the x or y-axis depending on the
        layout of the tree drawing. This is a convenient argument
        for visualizing discordance of trees.
    fixed_position: Sequence[float]
        The positions on the tip axis where ordered tips should
        be plotted. If None then default positions range(0, ntips)
        are used. By setting explicit positions tips can be
        spaced to better show discordance, or extinct taxa, or
        morphology. The order of positions applies to tips in
        order of the 'fixed_order' arg.

    Examples
    --------
    >>> tree = toytree.rtree.unittree(ntips=10)
    >>> tree.draw();
    >>> canvas, axes, mark = tree.draw(ts="o", scale_bar=True);
    >>>
    >>> # save drawing to file.
    >>> import toyplot.svg
    >>> toyplot.svg.render(canvas, "saved-plot.svg")

