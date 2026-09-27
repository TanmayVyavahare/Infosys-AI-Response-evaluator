import React, { useState, useRef } from 'react';
import type { EvaluationRequest, BatchEvaluationResponse, EvaluationResponse } from '../types/evaluation';
import { ResultsPanel } from './ResultsPanel';

interface BatchDashboardProps {
  onSubmit: (requests: EvaluationRequest[]) => Promise<void>;
  loading: boolean;
  elapsed: number;
  batchResult: BatchEvaluationResponse | null;
  onReset: () => void;
}

export function BatchDashboard({ onSubmit, loading, elapsed, batchResult, onReset }: BatchDashboardProps) {
  const [dragActive, setDragActive] = useState(false);
  const [csvRows, setCsvRows] = useState<string[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [selectedInspectRow, setSelectedInspectRow] = useState<EvaluationResponse | null>(null);
  const [inspectIndex, setInspectIndex] = useState<number | null>(null);
  
  // Header mappings
  const [questionCol, setQuestionCol] = useState('');
  const [responseCol, setResponseCol] = useState('');
  const [referenceCol, setReferenceCol] = useState('');
  const [sourceCol, setSourceCol] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Robust CSV parser
  const parseCSV = (text: string): string[][] => {
    const lines: string[][] = [];
    let row: string[] = [];
    let insideQuote = false;
    let entry = '';

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      const nextChar = text[i + 1];

      if (char === '"') {
        if (insideQuote && nextChar === '"') {
          entry += '"';
          i++; // Skip next quote
        } else {
          insideQuote = !insideQuote;
        }
      } else if (char === ',' && !insideQuote) {
        row.push(entry);
        entry = '';
      } else if ((char === '\r' || char === '\n') && !insideQuote) {
        if (char === '\r' && nextChar === '\n') {
          i++;
        }
        row.push(entry);
        lines.push(row);
        row = [];
        entry = '';
      } else {
        entry += char;
      }
    }
    if (entry || row.length > 0) {
      row.push(entry);
      lines.push(row);
    }
    return lines.filter(r => r.some(cell => cell.trim().length > 0));
  };

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      if (parsed.length > 1) {
        const fileHeaders = parsed[0].map(h => h.trim());
        setHeaders(fileHeaders);
        setCsvRows(parsed.slice(1));
        
        // Auto-detect columns
        const qIdx = fileHeaders.findIndex(h => /question|query|prompt/i.test(h));
        const rIdx = fileHeaders.findIndex(h => /response|output|ai|answer/i.test(h));
        const refIdx = fileHeaders.findIndex(h => /reference|ground_truth|golden/i.test(h));
        const sIdx = fileHeaders.findIndex(h => /source|context|document/i.test(h));
        
        if (qIdx !== -1) setQuestionCol(fileHeaders[qIdx]);
        if (rIdx !== -1) setResponseCol(fileHeaders[rIdx]);
        if (refIdx !== -1) setReferenceCol(fileHeaders[refIdx]);
        if (sIdx !== -1) setSourceCol(fileHeaders[sIdx]);
      } else {
        alert('CSV must contain a header row and at least one data row.');
      }
    };
    reader.readAsText(file);
  };

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
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const getMappedRequests = (): EvaluationRequest[] => {
    const qIndex = headers.indexOf(questionCol);
    const rIndex = headers.indexOf(responseCol);
    const refIndex = headers.indexOf(referenceCol);
    const sIndex = headers.indexOf(sourceCol);

    if (qIndex === -1 || rIndex === -1) return [];

    return csvRows.map(row => ({
      question: row[qIndex]?.trim() || '',
      ai_response: row[rIndex]?.trim() || '',
      reference_answer: refIndex !== -1 ? row[refIndex]?.trim() : undefined,
      source_document: sIndex !== -1 ? row[sIndex]?.trim() : undefined,
    })).filter(req => req.question.length > 0 && req.ai_response.length > 0);
  };

  const executeBatch = () => {
    const requests = getMappedRequests();
    if (requests.length === 0) {
      alert('Could not map fields. Please select valid header columns.');
      return;
    }
    onSubmit(requests);
  };

  const clearUpload = () => {
    setCsvRows([]);
    setHeaders([]);
    setQuestionCol('');
    setResponseCol('');
    setReferenceCol('');
    setSourceCol('');
    setSelectedInspectRow(null);
    setInspectIndex(null);
    onReset();
  };

  const mappedRequests = getMappedRequests();
  const isValidMapping = questionCol && responseCol && mappedRequests.length > 0;

  return (
    <div className="space-y-10 border border-white/5 bg-surface-900/10 p-8 rounded-2xl">
      {/* 1. Header Control */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">Batch Evaluation Dashboard</h2>
          <p className="text-xs text-surface-500 mt-1">Upload a CSV file containing multiple question-answer pairs to assess quality scores in batch.</p>
        </div>
        {(csvRows.length > 0 || batchResult) && (
          <button
            onClick={clearUpload}
            className="text-xs font-semibold px-4 py-2 rounded-xl border border-rose-500/25 bg-rose-950/20 text-rose-300 hover:bg-rose-900/35 hover:border-rose-400 cursor-pointer transition-all animate-fade-in"
          >
            Clear / Upload New CSV
          </button>
        )}
      </div>

      {/* 2. CSV File Ingestion Area */}
      {csvRows.length === 0 && !batchResult && (
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 bg-surface-950/20 min-h-[250px] flex flex-col items-center justify-center space-y-4 ${
            dragActive
              ? 'border-primary-500 bg-primary-950/15'
              : 'border-white/10 hover:border-primary-500/40 hover:bg-surface-900/30'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv"
            className="hidden"
          />
          <div className="w-16 h-16 rounded-2xl bg-surface-900/50 flex items-center justify-center text-primary-400 shadow-inner border border-white/5">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18V6a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 6v12a2.25 2.25 0 01-2.25 2.25H5.25" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Upload your Q&A Batch CSV</h3>
            <p className="text-xs text-surface-500 mt-1 max-w-sm mx-auto">Upload a standard CSV file with headers. We will parse and evaluate all pairs concurrently.</p>
          </div>
          <div className="flex gap-4">
            <button className="btn-primary py-2 px-5 text-xs font-semibold">Select CSV File</button>
            <button
              type="button"
              id="load-mock-csv-btn"
              onClick={(e) => {
                e.stopPropagation();
                const fileHeaders = ['Question', 'AI Response', 'Reference Answer'];
                const mockRows = [
                  ['Who discovered gravity?', 'Isaac Newton discovered gravity by watching an apple fall.', 'Sir Isaac Newton formulated the laws of gravity.'],
                  ['What is the speed of light?', 'The speed of light is 300000 km/s in a vacuum.', 'The speed of light is 299792458 meters per second.'],
                  ['What is photosynthesis?', 'Photosynthesis is the process plants use to convert sunlight into food.', 'Plants use photosynthesis to make glucose.']
                ];
                setHeaders(fileHeaders);
                setCsvRows(mockRows);
                setQuestionCol('Question');
                setResponseCol('AI Response');
                setReferenceCol('Reference Answer');
              }}
              className="text-xs font-semibold px-4 py-2 rounded-xl border border-primary-500/35 bg-primary-950/20 text-primary-300 hover:bg-primary-900/30 hover:border-primary-400 transition-all cursor-pointer"
            >
              Load Demo CSV Data
            </button>
          </div>
        </div>
      )}

      {/* 3. CSV Column Mapper */}
      {csvRows.length > 0 && !batchResult && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start animate-fade-in">
          {/* Mapping settings */}
          <div className="lg:col-span-4 glass-card p-6 bg-surface-900/40 rounded-xl space-y-5 border-white/5">
            <h3 className="text-[14px] font-bold text-white tracking-wide border-b border-white/5 pb-2">CSV Column Mapping</h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-[10px] font-black text-surface-400 tracking-wider">
                  QUESTION / QUERY COLUMN <span className="text-primary-400">*</span>
                </label>
                <select
                  value={questionCol}
                  onChange={(e) => setQuestionCol(e.target.value)}
                  className="input-field py-2.5 text-xs bg-surface-950 border-white/10"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[10px] font-black text-surface-400 tracking-wider">
                  AI RESPONSE COLUMN <span className="text-primary-400">*</span>
                </label>
                <select
                  value={responseCol}
                  onChange={(e) => setResponseCol(e.target.value)}
                  className="input-field py-2.5 text-xs bg-surface-950 border-white/10"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[10px] font-black text-surface-400 tracking-wider">
                  REFERENCE ANSWER COLUMN (OPTIONAL)
                </label>
                <select
                  value={referenceCol}
                  onChange={(e) => setReferenceCol(e.target.value)}
                  className="input-field py-2.5 text-xs bg-surface-950 border-white/10"
                >
                  <option value="">-- None / Skip --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[10px] font-black text-surface-400 tracking-wider">
                  SOURCE DOCUMENT / RAG COLUMN (OPTIONAL)
                </label>
                <select
                  value={sourceCol}
                  onChange={(e) => setSourceCol(e.target.value)}
                  className="input-field py-2.5 text-xs bg-surface-950 border-white/10"
                >
                  <option value="">-- None / Skip --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
            </div>

            <div className="pt-3">
              <button
                onClick={executeBatch}
                disabled={!isValidMapping}
                className="w-full bg-gradient-to-r from-primary-600 to-accent-purple hover:from-primary-500 hover:to-accent-purple/90 text-white font-bold py-3 px-5 rounded-xl shadow-lg shadow-primary-500/10 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs"
              >
                Run Batch Evaluation ({mappedRequests.length} rows)
              </button>
            </div>
          </div>

          {/* CSV Preview */}
          <div className="lg:col-span-8 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-black text-surface-400 tracking-wider">Ingested Row Preview</h3>
              <span className="text-[10px] font-semibold text-primary-400 bg-primary-950/50 px-2 py-0.5 rounded border border-primary-500/20">{csvRows.length} Rows Ingested</span>
            </div>
            
            <div className="glass-card overflow-x-auto border-white/5 bg-surface-900/15 max-h-[400px]">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/5 text-[10px] font-black text-surface-400 uppercase tracking-wider bg-surface-950/20">
                    <th className="p-3 w-12 text-center border-r border-white/5">Row</th>
                    {headers.map(h => (
                      <th key={h} className={`p-3 min-w-[150px] ${
                        h === questionCol || h === responseCol ? 'text-primary-400 font-bold bg-primary-950/10' : ''
                      }`}>
                        {h} {h === questionCol && '🎯'} {h === responseCol && '⚡'}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 bg-surface-950/5">
                  {csvRows.slice(0, 10).map((row, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="p-3 text-center text-surface-500 font-mono-code border-r border-white/5 bg-surface-950/10">{idx + 1}</td>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="p-3 truncate max-w-[200px] text-surface-300">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {csvRows.length > 10 && (
                <div className="p-3 text-center text-[10px] text-surface-500 border-t border-white/5 bg-surface-950/20">
                  Showing first 10 of {csvRows.length} rows...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 4. Loading State */}
      {loading && (
        <div className="glass-card p-12 flex flex-col items-center justify-center text-center border-white/5 bg-surface-900/20 space-y-4 animate-pulse">
          <div className="relative w-12 h-12 flex items-center justify-center">
            <span className="absolute inline-flex h-full w-full rounded-full bg-primary-500/15 animate-ping"></span>
            <div className="w-8 h-8 rounded-full border-2 border-primary-500/25 border-t-primary-500 animate-spin"></div>
          </div>
          <div>
            <h4 className="text-sm font-bold text-white tracking-wide mb-1">Evaluating Batch Request</h4>
            <p className="text-xs text-surface-500 max-w-sm mx-auto">Running concurrent judge agents on all items. This may take a moment depending on the model's throughput.</p>
          </div>
          <div className="text-xs text-primary-300 font-mono-code bg-primary-950/60 border border-primary-800/40 px-3 py-1.5 rounded-lg">
            Elapsed Time: {elapsed.toFixed(1)}s
          </div>
        </div>
      )}

      {/* 5. Aggregate Analytics Dashboard */}
      {batchResult && !loading && (
        <div className="space-y-10 animate-fade-in">
          {/* Summary Dashboard Grid */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            
            {/* Aggregated score card */}
            <div className="md:col-span-4 glass-card p-6 bg-surface-900/40 rounded-xl border-white/5 flex flex-col items-center justify-center text-center space-y-3 relative overflow-hidden">
              <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-primary-500 to-transparent absolute top-0 left-0"></div>
              <h3 className="text-xs font-black text-surface-400 tracking-wider">Average Batch Score</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-5xl font-black text-white leading-none">
                  {batchResult.average_score !== null ? (batchResult.average_score * 100).toFixed(0) : 'N/A'}
                </span>
                <span className="text-lg font-bold text-surface-500">/100</span>
              </div>
              <div className="w-full bg-surface-950/60 rounded-full h-2 max-w-[200px] border border-white/5 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-primary-500 to-accent-purple h-full rounded-full transition-all duration-500" 
                  style={{ width: `${(batchResult.average_score || 0) * 100}%` }}
                ></div>
              </div>
              <p className="text-[10px] text-surface-400 uppercase font-black">
                {batchResult.total_count} Evaluated Items
              </p>
            </div>

            {/* Verdict distributions */}
            <div className="md:col-span-4 glass-card p-6 bg-surface-900/40 rounded-xl border-white/5 space-y-3">
              <h3 className="text-xs font-black text-surface-400 tracking-wider">Verdict Distribution</h3>
              <div className="space-y-2.5">
                {Object.entries(batchResult.verdict_counts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([verdict, count]) => {
                    const pct = (count / batchResult.total_count) * 100;
                    let color = 'bg-surface-600';
                    if (verdict === 'Excellent' || verdict === 'Good') color = 'bg-emerald-500';
                    else if (verdict === 'Acceptable') color = 'bg-yellow-500';
                    else color = 'bg-rose-500';

                    return (
                      <div key={verdict} className="space-y-1">
                        <div className="flex justify-between text-[10px] font-semibold text-surface-300">
                          <span>{verdict}</span>
                          <span className="text-surface-400 font-mono-code">{count} ({pct.toFixed(0)}%)</span>
                        </div>
                        <div className="w-full bg-surface-950/50 rounded-full h-1.5 border border-white/[0.02] overflow-hidden">
                          <div 
                            className={`${color} h-full rounded-full`}
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Dimension Breakdown averages */}
            <div className="md:col-span-4 glass-card p-6 bg-surface-900/40 rounded-xl border-white/5 space-y-3">
              <h3 className="text-xs font-black text-surface-400 tracking-wider">Average Dimension Scores</h3>
              <div className="space-y-3">
                {Object.entries(batchResult.average_metrics).map(([metric, score]) => (
                  <div key={metric} className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="text-[11px] font-bold text-surface-300 uppercase tracking-wide">{metric}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-20 bg-surface-950/50 rounded-full h-1 border border-white/[0.02] overflow-hidden">
                        <div 
                          className="bg-primary-500 h-full rounded-full"
                          style={{ width: `${score * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-black text-white font-mono-code">{(score * 100).toFixed(0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* 6. Results List Table */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wide border-b border-white/5 pb-2">Evaluated Entries</h3>
            <div className="glass-card overflow-x-auto border-white/5 bg-surface-900/15">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/5 text-[10px] font-black text-surface-400 uppercase tracking-wider bg-surface-950/20">
                    <th className="p-3.5 w-12 text-center border-r border-white/5">Row</th>
                    <th className="p-3.5">Relevance strength</th>
                    <th className="p-3.5">Primary weakness</th>
                    <th className="p-3.5 w-24 text-center">Score</th>
                    <th className="p-3.5 w-40">Verdict</th>
                    <th className="p-3.5 w-24 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 bg-surface-950/5">
                  {batchResult.results.map((res, idx) => {
                    let verdictColor = 'text-surface-400 bg-surface-950/50 border-surface-900';
                    if (res.verdict === 'Excellent' || res.verdict === 'Good') {
                      verdictColor = 'text-emerald-400 bg-emerald-950/20 border-emerald-500/20';
                    } else if (res.verdict === 'Acceptable') {
                      verdictColor = 'text-yellow-400 bg-yellow-950/20 border-yellow-500/20';
                    } else {
                      verdictColor = 'text-rose-400 bg-rose-950/20 border-rose-500/20';
                    }

                    return (
                      <tr 
                        key={idx} 
                        className={`hover:bg-white/[0.01] transition-colors cursor-pointer ${
                          inspectIndex === idx ? 'bg-primary-950/10' : ''
                        }`}
                        onClick={() => {
                          setSelectedInspectRow(res);
                          setInspectIndex(idx);
                        }}
                      >
                        <td className="p-3.5 text-center text-surface-500 font-mono-code border-r border-white/5 bg-surface-950/10">{idx + 1}</td>
                        <td className="p-3.5 truncate max-w-[220px] text-surface-300 font-medium">
                          <span className="text-surface-300 block font-normal">{res.strengths[0] || 'No strengths flagged'}</span>
                        </td>
                        <td className="p-3.5 truncate max-w-[260px] text-surface-400">
                          {res.weaknesses[0] || 'Looks good'}
                        </td>
                        <td className="p-3.5 text-center">
                          <span className="text-xs font-black text-white font-mono-code bg-surface-950/60 border border-white/5 px-2 py-1 rounded">
                            {res.overall_score !== null ? (res.overall_score * 100).toFixed(0) : 'N/A'}
                          </span>
                        </td>
                        <td className="p-3.5">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${verdictColor}`}>
                            {res.verdict}
                          </span>
                        </td>
                        <td className="p-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => {
                              setSelectedInspectRow(res);
                              setInspectIndex(idx);
                            }}
                            className={`text-[10px] font-bold px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                              inspectIndex === idx
                                ? 'bg-primary-500 text-white border-primary-400'
                                : 'border-white/10 hover:border-primary-500/40 text-surface-300 hover:text-white'
                            }`}
                          >
                            Inspect Row
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 7. Row Inspector Detail Panel */}
          {selectedInspectRow && (
            <div className="space-y-4 pt-4 border-t border-white/5 animate-fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-black text-primary-400 uppercase tracking-wider">Inspect Row Detail Breakdown</h3>
                  <p className="text-[10px] text-surface-500">Currently reviewing details for Row #{ (inspectIndex || 0) + 1 }</p>
                </div>
                <button
                  onClick={() => {
                    setSelectedInspectRow(null);
                    setInspectIndex(null);
                  }}
                  className="text-xs font-bold text-rose-400 hover:underline cursor-pointer"
                >
                  Close Detail Inspector
                </button>
              </div>
              <ResultsPanel result={selectedInspectRow} />
            </div>
          )}

        </div>
      )}

    </div>
  );
}
