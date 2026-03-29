const SkeletonLoader = () => {
  return (
    <div className="grid grid-cols-2 gap-2 p-4 overflow-hidden animate-pulse">
      {/* LEFT: info column */}
      <div className="flex flex-col gap-3">
        {/* Company name + summary */}
        <div className="flex flex-col gap-2">
          <div className="h-12 w-52 bg-gray-200 rounded" />
          <div className="h-3 w-80 bg-gray-200 rounded" />
          <div className="h-3 w-20 bg-gray-200 rounded" />
        </div>

        {/* Truth score + analysis combined box */}
        <div className="bg-gray-200 rounded-md p-4 flex flex-col gap-4 flex-1">
          <div className="flex flex-col gap-2">
            <div className="h-3 w-24 bg-gray-200 rounded" />
            <div className="h-10 w-20 bg-gray-200 rounded" />
            <div className="h-4 w-16 bg-gray-200 rounded" />
            <div className="flex flex-col gap-1 mt-1">
              <div className="h-3 w-56 bg-gray-200 rounded" />
              <div className="h-3 w-56 bg-gray-200 rounded" />
              <div className="h-3 w-44 bg-gray-200 rounded" />
            </div>
          </div>
          <div className="border-t border-gray-100 pt-4 flex flex-col gap-2">
            <div className="h-3 w-20 bg-gray-200 rounded" />
            <div className="h-3 w-full bg-gray-200 rounded" />
            <div className="h-3 w-full bg-gray-200 rounded" />
            <div className="h-3 w-3/4 bg-gray-200 rounded" />
          </div>
        </div>
      </div>

      {/* RIGHT: two stacked satellite loaders */}
      <div className="flex flex-col gap-2">
        <div className="flex-1 flex flex-col gap-1">
          <div className="h-3 w-16 bg-gray-200 rounded" />
          <div className="flex-1 bg-gray-200 rounded-lg min-h-40" />
        </div>
        <div className="flex-1 flex flex-col gap-1">
          <div className="h-3 w-16 bg-gray-200 rounded" />
          <div className="flex-1 bg-gray-200 rounded-lg min-h-40" />
        </div>
      </div>
    </div>
  );
};

export default SkeletonLoader;
