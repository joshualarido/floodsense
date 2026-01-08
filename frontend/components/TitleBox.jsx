import { 
    FaHouseFloodWater 
} from "react-icons/fa6";

export default function TitleBox() {
  return (
    <div className="flex flex-row items-center justify-start gap-4
                    px-6 py-4 shadow-lg rounded-xl
                    bg-white">
      <span className="wave text-2xl text-primary-500"><FaHouseFloodWater /></span>
      <span className="font-primary text-xl text-primary-500 font-semibold">FloodSense Jakarta</span>
    </div>
  );
}
