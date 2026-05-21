"""
pipeline/viz — Reusable Manim scene library.

Each module exposes one configurable Scene subclass.  All public symbols
are re-exported here so pipeline code can do:

    from pipeline.viz import SOHCAHTOAScene, UnitCircleScene, ...
"""

from pipeline.viz.sohcahtoa            import SOHCAHTOAScene
from pipeline.viz.unit_circle          import UnitCircleScene
from pipeline.viz.trig_graph_sync      import TrigGraphSyncScene
from pipeline.viz.parameter_sweep      import ConicEccentricitySweepScene, FunctionFamilySweepScene
from pipeline.viz.equation_transform   import EquationTransformScene
from pipeline.viz.angle_sweep          import AngleSweepScene
from pipeline.viz.geometric_construction import ParabolaConstructionScene, EllipseConstructionScene
from pipeline.viz.linear_transform_plane import LinearTransformPlaneScene, ConicRotationScene
from pipeline.viz.coordinate_plane     import CoordinatePlaneScene
from pipeline.viz.step_reveal          import StepRevealScene
from pipeline.viz.equation_anatomy     import EquationAnatomyScene
from pipeline.viz.number_line          import NumberLineScene
from pipeline.viz.mistake_comparison   import MistakeComparisonScene
from pipeline.viz.vector_diagram       import VectorDiagramScene
from pipeline.viz.geometric_figure     import GeometricFigureScene
from pipeline.viz.matrix_transform     import MatrixTransformScene
from pipeline.viz.bar_chart            import BarChartScene
from pipeline.viz.probability_tree     import ProbabilityTreeScene
from pipeline.viz.venn_diagram         import VennDiagramScene
from pipeline.viz.balance_scale        import BalanceScaleScene
from pipeline.viz.threed_axes          import ThreeDAxesScene
from pipeline.viz.threed_vectors       import ThreeDVectorsScene
from pipeline.viz.threed_surface       import ThreeDSurfaceScene

__all__ = [
    "SOHCAHTOAScene",
    "UnitCircleScene",
    "TrigGraphSyncScene",
    "ConicEccentricitySweepScene",
    "FunctionFamilySweepScene",
    "EquationTransformScene",
    "AngleSweepScene",
    "ParabolaConstructionScene",
    "EllipseConstructionScene",
    "LinearTransformPlaneScene",
    "ConicRotationScene",
    "CoordinatePlaneScene",
    "StepRevealScene",
    "EquationAnatomyScene",
    "NumberLineScene",
    "MistakeComparisonScene",
    "VectorDiagramScene",
    "GeometricFigureScene",
    "MatrixTransformScene",
    "BarChartScene",
    "ProbabilityTreeScene",
    "VennDiagramScene",
    "BalanceScaleScene",
    "ThreeDAxesScene",
    "ThreeDVectorsScene",
    "ThreeDSurfaceScene",
]
