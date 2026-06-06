"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders wiki/answer markdown. [[wikilinks]] aren't real links in the wiki, so
// we render them as subtle inline chips rather than broken anchors.
function preprocessWikilinks(text: string): string {
  return text.replace(/\[\[([^\]]+)\]\]/g, (_m, inner) => `\`${inner}\``);
}

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-wiki">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {preprocessWikilinks(children || "")}
      </ReactMarkdown>
    </div>
  );
}
