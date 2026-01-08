import { useState } from "react";
import FloodMap from "../components/FloodMap";
import TitleBox from "../components/TitleBox";
import LegendBox from "../components/LegendBox";
import RegionBox from "../components/RegionBox";
import { predictFlood } from "./api/api";

function App() {
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!selectedPoint) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await predictFlood(
        selectedPoint.lat,
        selectedPoint.lng
      );
      setResult(res.data);
    } catch (err) {
      alert("Failed to analyze flood risk.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="absolute top-0 left-0 z-50 flex flex-col gap-4 m-4">
        <TitleBox />
        <LegendBox />
      </div>

      <div className="absolute top-0 right-0 z-50 flex flex-col gap-4 m-4">
        <RegionBox
          point={selectedPoint}
          result={result}
          onAnalyze={handleAnalyze}
          loading={loading}
        />
      </div>

      <div className="relative z-0">
        <FloodMap
          selectedPoint={selectedPoint}
          setSelectedPoint={(point) => {
            setSelectedPoint(point);
            setResult(null);
          }}
        />
      </div>
    </>
  );
}

export default App;
