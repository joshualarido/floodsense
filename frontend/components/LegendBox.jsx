import FloodRiskIcon from "./FloodRiskIcon";
import { 
    TbTriangleSquareCircleFilled 
} from "react-icons/tb";


export default function LegendBox() {
  return (
    <div className="flex flex-col justify-start items-start gap-4 bg-white rounded-xl p-4 shadow-xl
                    ">
        
        <h1 className="flex flex-row gap-2 justify-center items-center text-md font-primary font-semibold text-primary-500"><span className="text-2xl text-primary-500"><TbTriangleSquareCircleFilled /></span>Map Legend</h1>
        
        <div className="w-full h-px bg-primary-500/25" />

        <div className="flex flex-col justify-start items-start gap-4">
            <h2 className="flex flex-row gap-4 justify-start items-center
                            text-sm font-primary"><FloodRiskIcon risk="low"/> Low Risk of Flooding</h2>
            <h2 className="flex flex-row gap-4 justify-start items-center
                            text-sm font-primary"><FloodRiskIcon risk="medium"/> Medium Risk of Flooding</h2>
            <h2 className="flex flex-row gap-4 justify-start items-center
                            text-sm font-primary"><FloodRiskIcon risk="high"/> High Risk of Flooding</h2>
        </div>
    </div>
  );
}
