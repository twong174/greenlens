import { useState } from "react";

import SearchIcon from "@mui/icons-material/Search";

const LandingPage = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    alert(searchTerm);
  };

  return (
    <div className="h-screen w-full grid grid-rows-[auto_1fr] p-4">
      <h1 className="uppercase font-medium text-xl">GreenLens</h1>
      <div className="flex items-center justify-center">
        <div className="flex items-center gap-1">
          <div className="border rounded-md flex items-center gap-1 px-2">
            <SearchIcon fontSize="small" className="text-gray-400" />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="focus:outline-none text-xs p-2"
            />
          </div>
          <button
            type="submit"
            onClick={handleSearch}
            className="text-white bg-green-500 rounded-md px-3 py-2 cursor-pointer text-xs"
          >
            Search
          </button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
