"use client";

import { useRef, useState } from "react";

export default function UploadZone({
  onFile,
  loading,
}: {
  onFile: (file: File) => void;
  loading: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    if (files && files[0]) onFile(files[0]);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!loading) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !loading && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
        dragging
          ? "border-sky-400 bg-sky-50"
          : "border-slate-300 bg-white hover:border-slate-400"
      } ${loading ? "pointer-events-none opacity-60" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {loading ? (
        <p className="text-sm font-medium text-slate-600">
          Analyzing site plan&hellip;
        </p>
      ) : (
        <>
          <p className="text-sm font-semibold text-slate-700">
            Drop a site-plan PDF here, or click to browse
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Lot dimensions, building footprint, setbacks, and parking
          </p>
        </>
      )}
    </div>
  );
}
