import React, { useState, useRef, useEffect } from 'react';
import type { EvaluationRequest } from '../types/evaluation';

interface EvaluationFormProps {
  onSubmit: (request: EvaluationRequest) => void;
  loading: boolean;
  elapsed: number;
  onCancel: () => void;
}

const PRESET_DEMO = {
  question: 'Who was the first President of the United States and when did he serve?',
  ai_response: 'George Washington was the first President of the United States, serving from 1789 to 1797.',
  reference_answer: 'George Washington served as the first President of the United States from 1789 to 1797.',
  source_document: 'George Washington (1732-1799) served as the first President of the United States from April 30, 1789 to March 4, 1797.',
};

export function EvaluationForm({ onSubmit, loading, elapsed, onCancel }: EvaluationFormProps) {
  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [sourceDocument, setSourceDocument] = useState('');
  
  // File drag-and-drop state
  const [fileError, setFileError] = useState('');
  const [reading, setReading] = useState(false);
  const readVersion = useRef(0);
  useEffect(() => () => { readVersion.current++; }, []);
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canSubmit = question.trim().length > 0 && aiResponse.trim().length > 0 && !loading && !reading;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      question: question.trim(),
      ai_response: aiResponse.trim(),
      reference_answer: referenceAnswer.trim() || undefined,
      source_document: sourceDocument.trim() || undefined,
    });
  };

  const loadSampleDemo = () => {
    setQuestion(PRESET_DEMO.question);
    setAiResponse(PRESET_DEMO.ai_response);
    setReferenceAnswer(PRESET_DEMO.reference_answer);
    setSourceDocument(PRESET_DEMO.source_document);
    readVersion.current++;
    setReading(false);
    setFileError('');
    setFileName(null);
    setFileSize(null);
  };

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleFile(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      handleFile(file);
    }
  };

  const handleFile = async (file: File) => {
    if (loading) return;
    const version = ++readVersion.current;
    setReading(false);
    setFileError('');
    if (!/\.(txt|md|json)$/i.test(file.name)) {
      setFileError('Choose a .txt, .md, or .json file. PDFs and Word documents are not supported here.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setFileError('This file is too large. Choose a file smaller than 5 MB.');
      return;
    }
    setReading(true);
    try {
      const text = await file.text();
      if (version !== readVersion.current) return;
      if (!text.trim() || text.includes('\0')) throw new Error('Choose a non-empty plain text file.');
      setSourceDocument(text);
      setFileName(file.name);
      setFileSize((file.size / 1024).toFixed(1) + ' KB');
    } catch (error) {
      if (version === readVersion.current) setFileError(error instanceof Error ? error.message : 'Could not read this file. Try again.');
    } finally {
      if (version === readVersion.current) setReading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removeFile = () => {
    readVersion.current++;
    setReading(false);
    setFileError('');
    setSourceDocument('');
    setFileName(null);
    setFileSize(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <form onSubmit={handleSubmit} aria-busy={loading}>
      <fieldset disabled={loading} className="space-y-5 min-w-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">What would you like to review?</h2>
          <p className="mt-1 text-xs text-surface-400 leading-relaxed">The question and AI response are all you need to get started.</p>
        </div>
        <button
          type="button"
          onClick={loadSampleDemo}
          className="shrink-0 text-xs font-semibold px-3 py-2 rounded-lg border border-primary-500/35 bg-primary-950/20 text-primary-300 hover:bg-primary-900/30 hover:border-primary-400 transition-all cursor-pointer"
        >
          Try an example
        </button>
      </div>

      {/* Question Field */}
      <div className="space-y-2">
        <label htmlFor="input-question" className="block text-[11px] font-black text-surface-400 tracking-wider">
          Question <span className="text-primary-400 text-xs">*</span>
        </label>
        <textarea
          id="input-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What did the user ask the AI?"
          rows={3}
          className="input-field"
          required
        />
      </div>

      {/* AI Response Field */}
      <div className="space-y-2">
        <label htmlFor="input-ai-response" className="block text-[11px] font-black text-surface-400 tracking-wider">
          AI response <span className="text-primary-400 text-xs">*</span>
        </label>
        <textarea
          id="input-ai-response"
          value={aiResponse}
          onChange={(e) => setAiResponse(e.target.value)}
          placeholder="Paste the answer you want to assess..."
          rows={6}
          className="input-field"
          required
        />
      </div>

      <details className="supporting-details" open={sourceDocument ? true : undefined}>
      <summary>Improve your review <span className="text-surface-400 font-normal">· optional</span></summary>
      <p className="text-sm text-surface-400 mt-3 mb-4">Add a trusted answer or source to check facts. Without supporting material, some checks may be unavailable.</p>
      {/* Reference Answer */}
      <div className="space-y-2">
        <label htmlFor="input-reference" className="block text-[11px] font-black text-surface-400 tracking-wider">
          Reference answer <span className="normal-case font-medium text-surface-500">(optional)</span>
        </label>
        <textarea
          id="input-reference"
          value={referenceAnswer}
          onChange={(e) => setReferenceAnswer(e.target.value)}
          placeholder="Add the ideal or verified answer to check factual accuracy..."
          rows={3}
          className="input-field"
        />
      </div>

      {/* Source Document Ingestion */}
      <div className="space-y-2">
        <label htmlFor="source-text" className="block text-[11px] font-black text-surface-400 tracking-wider">
          Source material <span className="normal-case font-medium text-surface-500">(optional)</span>
        </label>
        
        <textarea id="source-text" className="input-field" rows={3} value={sourceDocument}
          onChange={(e) => { setSourceDocument(e.target.value); setFileName(null); setFileSize(null); }}
          placeholder="Paste supporting text, or upload a text file below..." disabled={reading} />
        {fileError && <p role="alert" className="text-sm text-rose-300">{fileError}</p>}
        {reading && <p role="status" className="text-sm text-primary-300">Reading file…</p>}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".txt,.md,.json"
          className="hidden"
          id="file-upload-input"
        />

        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          className={`border border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 bg-surface-950/40 relative flex flex-col items-center justify-center min-h-[120px] ${
            dragActive
              ? 'border-primary-500 bg-primary-950/15'
              : 'border-white/10 hover:border-primary-500/40 hover:bg-surface-900/30'
          }`}
        >
          {fileName ? (
            <div className="flex flex-col items-center justify-center space-y-2 animate-fade-in w-full px-4" onClick={(e) => e.stopPropagation()}>
              <svg className="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <div className="text-xs font-semibold text-white truncate max-w-full">
                {fileName}
              </div>
              <div className="text-[10px] text-surface-400">
                {fileSize}
              </div>
              <button
                type="button"
                onClick={removeFile}
                className="mt-1 text-[10px] font-bold text-rose-400 hover:text-rose-300 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <span>Remove file</span>
              </button>
            </div>
          ) : (
            <>
              {/* Tray Arrow Up Icon */}
              <svg className="w-7 h-7 text-surface-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              <div className="text-xs font-medium text-surface-300">
                Drop a text file here or <button type="button" onClick={() => fileInputRef.current?.click()} className="text-primary-300 underline">choose a file</button>
              </div>
              <div className="text-[10px] text-surface-500 mt-1">
                Use .txt, .md, or .json files up to 5 MB
              </div>
            </>
          )}
        </div>
      </div>

      </details>
      {/* Submit Button */}
      <div className="pt-2">
        {!canSubmit && !loading && <p className="text-sm text-surface-400 mb-3">{reading ? 'Wait for your file to finish loading.' : 'Add a question and an AI response to start.'}</p>}
        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full bg-gradient-to-r from-primary-600 to-accent-purple hover:from-primary-500 hover:to-accent-purple/90 text-white font-bold py-3.5 px-6 rounded-xl flex items-center justify-center gap-2.5 shadow-lg shadow-primary-500/20 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 text-sm"
        >
          {loading ? (
            <>
              <svg className="animate-spin w-4.5 h-4.5 text-white/90" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
                <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              <span className="tracking-wide">Reviewing response ({elapsed.toFixed(1)}s)...</span>
            </>
          ) : (
            <>
              {/* Play symbol */}
              <svg className="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              <span className="font-bold tracking-wide">Review response</span>
            </>
          )}
        </button>
      </div>
      </fieldset>
      {loading && <button type="button" className="btn-ghost w-full mt-3 py-3 text-sm" onClick={onCancel}>Cancel review</button>}
    </form>
  );
}
