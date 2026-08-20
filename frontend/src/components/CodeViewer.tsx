import React, { useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { X } from '@phosphor-icons/react';

interface CodeViewerProps {
  file: string;
  content: string;
  language?: string;
  highlightLine?: number;
  onClose: () => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  file,
  content,
  language = 'python',
  highlightLine,
  onClose,
}) => {
  const editorRef = useRef<any>(null);

  useEffect(() => {
    if (editorRef.current && highlightLine) {
      // Scroll to and highlight the specified line
      editorRef.current.revealLineInCenter(highlightLine);
      editorRef.current.setSelection({
        startLineNumber: highlightLine,
        startColumn: 1,
        endLineNumber: highlightLine,
        endColumn: 1000,
      });
    }
  }, [highlightLine, content]);

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
    if (highlightLine) {
      editor.revealLineInCenter(highlightLine);
      editor.setSelection({
        startLineNumber: highlightLine,
        startColumn: 1,
        endLineNumber: highlightLine,
        endColumn: 1000,
      });
    }
  };

  return (
    <div className="flex flex-col h-full bg-cardBg border border-cardBorder rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-cardBorder bg-cardBg">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-xs font-mono text-slate-400 truncate">{file}</span>
          {highlightLine && (
            <span className="text-xs font-mono text-accentPurple">
              Line {highlightLine}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition p-1"
          aria-label="Close"
        >
          <X size={18} weight="bold" />
        </button>
      </div>

      {/* Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          language={language}
          value={content}
          theme="vs-dark"
          onMount={handleEditorDidMount}
          options={{
            readOnly: true,
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            folding: true,
            renderLineHighlight: 'all',
            selectionHighlight: true,
            occurrencesHighlight: true,
            fontFamily: 'Fira Code, Courier New, monospace',
            fontLigatures: true,
          }}
        />
      </div>
    </div>
  );
};
