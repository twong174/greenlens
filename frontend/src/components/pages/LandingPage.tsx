const LandingPage = () => {
  return (
    <div className="h-screen w-full grid grid-rows-[auto_1fr] p-4">
      <h1 className="uppercase font-medium text-xl">GreenLens</h1>
      <div className=" flex items-center justify-center">
        <div className="border rounded-md flex items-center gap-2">
          <input type="text" className="focus:outline-none text-xs p-2 " />
          <button type="submit" className="border text-white bg-green-500 rounded"> Search </button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
