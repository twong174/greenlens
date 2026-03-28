import { Link } from "react-router-dom";
import SpaIcon from '@mui/icons-material/Spa';

const CompanyPage = () => {
  return (
    <>
      <div className="h-screen w-full p-4 grid grid-rows-[auto_1fr]">
        <Link to="/" className="flex items-center gap-0.5">
        
        <SpaIcon fontSize="small" className="text-emerald-800"/> 
        <h1 className=" font-semibold text-xl text-emerald-800">GreenLens</h1></Link>
        <div className="bg-red-100"></div>
      </div>
    </>
  );
};

export default CompanyPage;
