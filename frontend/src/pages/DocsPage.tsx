import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { listDocFiles, getDocFile } from "../api/client";

interface DocFile {
  slug: string;
  filename: string;
}

export default function DocsPage() {
  const [files, setFiles] = useState<DocFile[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDocFiles()
      .then((data) => {
        setFiles(data);
        if (data.length > 0) {
          setActiveSlug(data[0].slug);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!activeSlug) return;
    setLoading(true);
    getDocFile(activeSlug)
      .then((data) => setContent(data.content))
      .finally(() => setLoading(false));
  }, [activeSlug]);

  function formatLabel(filename: string) {
    return filename
      .replace(/\.md$/, "")
      .replace(/^\d+-/, "")
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  return (
    <div className="flex gap-6 -mx-6 lg:-mx-8 -my-8 h-[calc(100vh-0px)]">
      {/* Secondary sidebar */}
      <aside className="w-56 shrink-0 bg-white border-r border-gray-200 overflow-y-auto py-6 px-3">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-3">
          Documents
        </h2>
        <nav className="space-y-0.5">
          {files.map((f) => (
            <button
              key={f.slug}
              onClick={() => setActiveSlug(f.slug)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                activeSlug === f.slug
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              {formatLabel(f.filename)}
            </button>
          ))}
        </nav>
      </aside>

      {/* Content area */}
      <main className="flex-1 overflow-y-auto py-8 pr-6 lg:pr-8">
        {loading ? (
          <div className="text-gray-500 text-sm">Loading...</div>
        ) : !activeSlug ? (
          <div className="text-center text-gray-400 py-20">
            <p className="text-lg">No documents found</p>
            <p className="text-sm mt-1">Add markdown files to the knowledge/ directory</p>
          </div>
        ) : (
          <article className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-900 prose-pre:text-gray-100">
            <ReactMarkdown>{content}</ReactMarkdown>
          </article>
        )}
      </main>
    </div>
  );
}
