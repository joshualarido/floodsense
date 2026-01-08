import { TbMapPinFilled } from "react-icons/tb";
import FloodRiskIcon from "./FloodRiskIcon";

/* ---------- helpers ---------- */
const getRiskLevel = (riskValue) => {
  if (riskValue <= 30) return "low";
  if (riskValue <= 60) return "medium";
  return "high";
};

const getRiskLabel = (riskLevel) => {
  return {
    low: "Low Risk",
    medium: "Medium Risk",
    high: "High Risk",
  }[riskLevel];
};

const FEATURE_LABELS = [
  {
    key: "precip_1d",
    label: "Current Rainfall (1 Day)",
    unit: "mm",
  },
  {
    key: "precip_3d",
    label: "Rainfall (Last 3 Days)",
    unit: "mm",
  },
  {
    key: "jrc_perm_water",
    label: "Permanent Water Occurrence",
    unit: "%",
  },
  {
    key: "NDVI",
    label: "Vegetation Index (NDVI)",
    unit: "",
  },
  {
    key: "NDWI",
    label: "Water Index (NDWI)",
    unit: "",
  },
  {
    key: "landcover",
    label: "Land Cover Type",
    unit: "",
  },
  {
    key: "elevation",
    label: "Elevation",
    unit: "m ASL",
  },
  {
    key: "slope",
    label: "Slope",
    unit: "°",
  },
  {
    key: "aspect",
    label: "Aspect",
    unit: "°",
  },
  {
    key: "upstream_area",
    label: "Upstream Catchment Area",
    unit: "km²",
  },
  {
    key: "TWI",
    label: "Topographic Wetness Index (TWI)",
    unit: "",
  },
];

/* ---------- component ---------- */
export default function RegionBox({
  point,
  result,
  onAnalyze,
  loading,
}) {
  const rawRiskScore = result?.ai_response?.risk_score;

  const riskValue =
    typeof rawRiskScore === "number"
      ? Math.round(rawRiskScore * 100)
      : null;

  const riskLevel =
    typeof riskValue === "number" ? getRiskLevel(riskValue) : null;
  
  const formatValue = (value) => {
    if (typeof value !== "number") return value;
    if (Number.isInteger(value)) return value;
    return value.toFixed(5);
  };

  return (
    <div className="
      flex flex-col gap-4
      bg-white/95 rounded-xl p-4 shadow-lg
      bg-gradient-to-b from-white to-gray-200
      w-[300px]
    ">
      {/* Header */}
      <h1 className="flex flex-row gap-2 items-center text-md font-primary font-semibold text-primary-500">
        <span className="text-2xl text-primary-500">
          <TbMapPinFilled />
        </span>
        Region Details
      </h1>

      <div className="w-full h-px bg-primary-500/25" />

      {!point && (
        <p className="text-sm font-primary text-gray-500">
          Click on the map to select a location.
        </p>
      )}

      {point && (
        <div className="flex flex-col gap-3 text-sm font-primary">
          <div className="flex flex-row gap-4">
            <div>
              <span className="text-gray-500">Latitude</span>
              <div className="font-medium">{point.lat.toFixed(5)}</div>
            </div>

            <div>
              <span className="text-gray-500">Longitude</span>
              <div className="font-medium">{point.lng.toFixed(5)}</div>
            </div>
          </div>

          {!result && (
            <button
              onClick={onAnalyze}
              disabled={loading}
              className="
                mt-2 w-full py-2 rounded-lg
                bg-primary-500 text-white font-semibold
                hover:bg-primary-600 transition
                disabled:opacity-50
              "
            >
              {loading ? "Analyzing..." : "Analyze Flood Risk"}
            </button>
          )}

          {result && (
            <>
              {/* Risk summary */}
              <div className="flex items-center gap-3 mt-2">
                <FloodRiskIcon risk={riskLevel} />
                <div>
                  <div className="text-gray-500 text-xs">Flood Risk</div>
                  <div className="font-semibold capitalize">
                    {getRiskLabel(riskLevel)} ({riskValue}%)
                  </div>
                </div>
              </div>

              {/* Conditions */}
              <div className="mt-3">
                <div className="text-xs font-semibold text-gray-500 mb-2">
                  Conditions
                </div>

                <div className="flex flex-col gap-2">
                  {FEATURE_LABELS.map(({ label, unit }, index) => (
                    result.features?.[index] !== undefined && (
                      <div
                        key={label}
                        className="flex justify-between text-xs"
                      >
                        <span className="text-gray-600">{label}</span>
                        <span className="font-medium text-gray-800">
                          {formatValue(result.features[index])} {unit}
                        </span>
                      </div>
                    )
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
