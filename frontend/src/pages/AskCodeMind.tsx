import React, { useState } from 'react';
import { Send, FileCode, Cpu, ListCollapse, Database, GitBranch } from 'lucide-react';
import { api } from '../services/api';
import { AskResponse } from '../types';
import { DependencyPath } from '../components/DependencyPath';

interface AskCodeMindProps {
  repositoryId: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  responseObj?: AskResponse;
}

export const AskCodeMind: React.FC<AskCodeMindProps> = ({ repositoryId }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading || !repositoryId) return;

    const userQuestion = question;
    setQuestion('');
    setError(null);
    setLoading(true);

    // Append user message
    setChat((prev) => [...prev, { role: 'user', content: userQuestion }]);

    try {
      const resp = await api.askCodeMind(repositoryId, userQuestion);
      setChat((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: resp.answer,
          responseObj: resp,
        },
      ]);
    } catch (err: any) {
      setError(err.message || 'Failed to get answer from CodeMind.');
    } finally {
      setLoading(false);
    }
  };

  if (!repositoryId) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono">
        Please select or ingest a repository on the Overview dashboard first.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] border border-cardBorder rounded-lg bg-cardBg overflow-hidden text-sm">
      {/* Header */}
      <div className="px-5 py-3 border-b border-cardBorder bg-cardBg flex items-center justify-between">
        <h2 className="text-base font-bold font-mono text-white flex items-center gap-2">
          <Cpu size={18} className="text-accentPurple" /> Ask CodeMind
        </h2>
        <span className="text-[10px] font-mono text-slate-400 bg-darkBg px-2 py-0.5 border border-cardBorder rounded">
          Active Repo: {repositoryId}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 bg-darkBg/30">
        {chat.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-3">
            <Cpu size={40} className="text-slate-600 animate-pulse" />
            <h3 className="font-bold text-slate-400 font-mono">Grounded Code Graph Q&A</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Ask natural language questions about your repository structure. Answers are grounded strictly in code entities and dependency paths fetched from HydraDB.
            </p>
            <div className="flex flex-wrap gap-2 justify-center pt-2 font-mono text-[10px]">
              <span className="bg-slate-900 border border-cardBorder px-2 py-1 rounded text-slate-400">
                &quot;What calls authenticate_user?&quot;
              </span>
              <span className="bg-slate-900 border border-cardBorder px-2 py-1 rounded text-slate-400">
                &quot;Which tests cover routes.py?&quot;
              </span>
            </div>
          </div>
        )}

        {chat.map((msg, idx) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={idx}
              className={`flex flex-col max-w-4xl ${
                isUser ? 'ml-auto items-end' : 'mr-auto items-start'
              }`}
            >
              <span className="text-[10px] text-slate-500 font-mono mb-1">
                {isUser ? 'User' : 'CodeMind AI'}
              </span>
              <div
                className={`p-4 rounded-lg leading-relaxed ${
                  isUser
                    ? 'bg-accentPurple text-white font-medium shadow-lg shadow-violet-900/10'
                    : 'bg-cardBg border border-cardBorder text-slate-200'
                }`}
              >
                {msg.content}
              </div>

              {/* Citations & Evidence Panel for Assistant responses */}
              {!isUser && msg.responseObj && (
                <div className="mt-4 w-full space-y-4">
                  {/* Graph Paths */}
                  {msg.responseObj.dependency_paths && msg.responseObj.dependency_paths.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">
                        Dependency Paths (Grounded in HydraDB)
                      </span>
                      {msg.responseObj.dependency_paths.map((path, pathIdx) => (
                        <DependencyPath key={pathIdx} path={path} />
                      ))}
                    </div>
                  )}

                  {/* Document/Code Chunks */}
                  {msg.responseObj.evidence && msg.responseObj.evidence.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">
                        Evidence Citations
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {msg.responseObj.evidence.map((ev, evIdx) => (
                          <div
                            key={evIdx}
                            className="bg-slate-950 border border-cardBorder rounded p-3 font-mono text-[11px]"
                          >
                            <div className="flex items-center justify-between mb-1.5 pb-1 border-b border-cardBorder">
                              <span className="text-[10px] font-bold text-accentBlue">
                                {ev.entity_type}: {ev.entity_name}
                              </span>
                              {ev.file && (
                                <span className="text-[9px] text-slate-500">
                                  {ev.file}
                                </span>
                              )}
                            </div>
                            <p className="text-slate-400 italic text-[10px] leading-relaxed line-clamp-3">
                              &quot;{ev.text}&quot;
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-2 text-slate-500 font-mono text-xs">
            <Cpu size={16} className="animate-spin text-accentPurple" /> Thinking...
          </div>
        )}

        {error && (
          <div className="bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-3 font-mono text-xs max-w-2xl">
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-cardBorder bg-cardBg flex gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about the repository connections..."
          disabled={loading}
          className="flex-1 bg-darkBg border border-cardBorder rounded px-4 py-3 text-slate-200 font-mono text-xs focus:outline-none focus:border-accentPurple placeholder:opacity-50 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="bg-accentPurple hover:bg-violet-600 active:bg-violet-700 disabled:opacity-50 text-white p-3 rounded transition duration-150 flex items-center justify-center shrink-0"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
};
