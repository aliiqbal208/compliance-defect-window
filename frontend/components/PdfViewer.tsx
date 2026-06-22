export default function PdfViewer({ url }: { url: string }) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
        <h3 className="text-sm font-semibold text-slate-700">Annotated Plan</h3>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-sky-600 hover:text-sky-700"
        >
          Open in new tab
        </a>
      </div>
      <iframe
        src={url}
        title="Annotated site plan"
        className="h-[640px] w-full rounded-b-xl"
      />
    </div>
  );
}
