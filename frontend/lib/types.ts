export type Status = "PASS" | "FAIL" | "UNKNOWN";

export interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page: number;
}

export interface Field {
  name: string;
  value: number | null;
  unit: string;
  confidence: number;
  source: "vision" | "text" | "derived";
  bbox: BBox | null;
  note: string | null;
}

export interface CheckResult {
  rule_id: string;
  label: string;
  field: string;
  required: string;
  actual: string | null;
  actual_value: number | null;
  status: Status;
  deficiency: number | null;
  message: string | null;
  confidence: number;
  bbox: BBox | null;
}

export interface AnalyzeResponse {
  id: string;
  backend: string;
  source_filename: string;
  compliant: boolean;
  summary: { passed: number; failed: number; unknown: number };
  checks: CheckResult[];
  fields: Record<string, Field>;
  warnings: string[];
  annotated_pdf_url: string;
}

// Display order + human labels for the extracted values panel.
export const FIELD_LABELS: Record<string, string> = {
  lot_width: "Lot Width",
  lot_depth: "Lot Depth",
  lot_area: "Lot Area",
  building_footprint_width: "Footprint Width",
  building_footprint_depth: "Footprint Depth",
  building_footprint_area: "Building Footprint",
  lot_coverage: "Lot Coverage",
  building_height: "Building Height",
  front_setback: "Front Setback",
  rear_setback: "Rear Setback",
  side_setback: "Side Setback",
  parking_stalls: "Parking Stalls",
};
