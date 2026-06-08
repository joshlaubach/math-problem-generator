export type GridType = 'square' | 'dotted' | 'isometric' | 'blank'

export type DrawTool =
  | 'select' | 'hand'
  | 'pen' | 'highlight' | 'eraser'
  | 'line' | 'arrow'
  | 'text' | 'latex'
  | 'rect' | 'circle' | 'ellipse'
  | 'triangle-free' | 'triangle-right' | 'triangle-iso'
  | 'parallelogram' | 'rhombus' | 'trapezoid'
  | 'polygon-regular'
  | 'arc' | 'sector' | 'annulus'
  | 'angle-marker' | 'right-angle-marker'
  | 'line-segment' | 'brace' | 'dot'
  | 'number-line' | 'vector' | 'venn' | 'matrix'
  | 'axes' | 'slider' | 'protractor'

export interface MathWhiteboardProps {
  mode?: 'session' | 'full'
  theme?: 'light' | 'dark'
  userId?: string
  onSnapshot?: (b64: string) => void
}

export interface ShapeClasses {
  FabricFreeTriangle: any
  FabricRightTriangle: any
  FabricIsoTriangle: any
  FabricRegularPolygon: any
  FabricAngleMarker: any
  FabricRightAngleMarker: any
  FabricNumberLine: any
  FabricBrace: any
  FabricDot: any
  FabricVenn: any
  FabricMatrix: any
  FabricVector: any
  FabricLineSegment: any
  FabricParallelogram: any
  FabricRhombus: any
  FabricTrapezoid: any
  FabricArc: any
  FabricSector: any
  FabricAnnulus: any
  FabricProtractor: any
  FabricAxes: any
  FabricSlider: any
}

export const SESSION_TOOLS: DrawTool[] = [
  'select', 'hand',
  'pen', 'highlight', 'eraser',
  'line', 'arrow',
  'text', 'latex',
  // shapes and math objects accessible via popup
  'rect', 'circle', 'triangle-free',
  'angle-marker', 'right-angle-marker', 'dot',
  'axes', 'number-line', 'vector',
]
