import { FaWater } from "react-icons/fa";

const FloodRiskIcon = ({ risk }) => {
  const riskBgClass = {
    low: "bg-low",
    medium: "bg-warning",
    high: "bg-primary-500",
  }[risk] || "bg-low";

  return (
    <div className={`p-2 rounded-full ${riskBgClass}`}>
      <div className="text-white text-xl">
        <FaWater />
      </div>
    </div>
  );
};

export default FloodRiskIcon;
