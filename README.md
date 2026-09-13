# emergent

This fork modernizes the original C++ Emergent neural network simulator for
Clang 24 nightly, Qt 6.12 Beta 4, and C++17. It retains the CSS (C Super Script)
interpreter, reflected object system, and Coin/Quarter 3D interface.

See [modern stack setup and verification](tools/toolchain/README.md) for the
pinned SDK, build instructions, and test commands. C++ builds require
`-Wall -Wextra -Werror -Woverloaded-virtual`, with no warning suppression flags.

The original [emer/cemer](https://github.com/emer/cemer) history, authorship,
and licenses are preserved. Its upstream team moved development to the
[Go implementation](https://github.com/emer/emergent). Historical C++
documentation is on the [upstream wiki](https://github.com/emer/cemer/wiki).

Historical releases include [8.6.1 sources](https://github.com/emer/cemer/releases/tag/v8.6.1),
[8.5.2 packages](https://github.com/emer/cemer/releases/tag/v8.5.2), and
[8.5.1 dependencies](https://github.com/emer/cemer/releases/tag/v8.5.1).

# About

*emergent* is a comprehensive neural network simulator that enables the creation and analysis of complex, sophisticated models of the brain in the world; features:

* Full browser and 3D GUI for constructing, visualizing, & interacting.
    + Accessible to non-programmers
    + But also highly productive for experts, used daily in scientific research.
    
* Powerful C++ scripting language, `css` (not ''that'' css), GUI `Program`ming environment (IDE) -- `TypeAccess` access to C++.

* Rich, dynamic, embodied environments for training networks:
    + `DataTable` for network inputs and `DataProc`, `DataAnal`, `DataGen` (filtering, grouping, sorting, dimensionality reduction, graphing, etc).
    
    + Newtonian physics simulator for Virtual Environment, e.g., a biophysically realistic human arm, and realistic embodied, dynamic vision.
    
    + Sensory filtering for vision, audition, and vocal-tract speech.
    
* Many classic neural network algorithms and variants: Backpropagation (e.g., deep convolutional neural networks), Constraint Satisfaction, Self Organizing, and the Leabra algorithm which incorporates many of the most important features from each of these algorithms, in a biologically consistent manner.  Also, symbolic / subsymbolic ACT-R.

    + Highly optimized vector-based back-end code with thread-specific memory allocation, and GPU (CUDA); Convenient compute cluster for GUI-based job control and data management.
    
* In use for decades, for hundreds of scientific publications from a variety of different labs.  Detailed models of the hippocampus, prefrontal cortex, basal ganglia, visual cortex, cerebellum, etc.

    + Direct descendant of earlier simulators: PDP (1986) and PDP++ (1995).
