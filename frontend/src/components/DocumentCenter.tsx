/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store';
import { useParams, useNavigate } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Loader2, X, Send } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export function DocumentCenter() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [permit, setPermit] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestReport, setLatestReport] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Chat state
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeViolation, setActiveViolation] = useState<any>(null);
  const [chatMessages, setChatMessages] = useState<Array<{role: string, content: string}>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    const fetchPermit = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/permits/${id}`);
        setPermit(res.data);

        if (res.data.submissions && res.data.submissions.length > 0) {
            const sorted = [...res.data.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            try {
                const report = JSON.parse(sorted[0].report_json);
                setLatestReport(report);
            } catch(e) {
                console.error("Failed to parse report json", e);
            }
        }
      } catch (err) {
        console.error("Failed fetching permit", err);
      }
    };

    fetchPermit();
  }, [id, user, navigate]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleResubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('permit_id', id as string);

    try {
      await axios.post(`${API_URL}/api/analyze-plan`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const res = await axios.get(`${API_URL}/api/permits/${id}`);
      setPermit(res.data);
      if (res.data.submissions && res.data.submissions.length > 0) {
          const sorted = [...res.data.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
          setLatestReport(JSON.parse(sorted[0].report_json));
      }

      setFile(null);
      if (fileInputRef.current) {
          fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'An error occurred while analyzing the plan.');
    } finally {
      setLoading(false);
    }
  };

  const getDisplayId = (id: number) => {
    return `#BP-2024-${String(id).padStart(4, '0')}`;
  };

  const openChatForViolation = (violation: any) => {
    setActiveViolation(violation);
    setChatMessages([
      {
        role: "assistant",
        content: `Hi there! You're asking about the violation for section ${violation.section}. How can I help you?`
      }
    ]);

    const formattedViolationText = `I have a question about this violation:\nSection: ${violation.section}\nDescription: ${violation.description}\nSuggestion: ${violation.suggestion}`;
    setChatInput(formattedViolationText);
    setIsChatOpen(true);
  };

  const sendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !activeViolation) return;

    const userMessage = { role: "user", content: chatInput };
    const newMessages = [...chatMessages, userMessage];

    setChatMessages(newMessages);
    setChatInput('');
    setChatLoading(true);

    try {
      const payload = {
        messages: newMessages,
        permit_id: id,
        violation: activeViolation
      };
      const res = await axios.post(`${API_URL}/api/chat`, payload);

      if (res.data && res.data.choices && res.data.choices.length > 0) {
        const assistantMessage = res.data.choices[0].message;
        setChatMessages([...newMessages, assistantMessage]);
      }
    } catch (err) {
      console.error("Failed to send chat message", err);
      setChatMessages([...newMessages, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const closeChat = () => {
    setIsChatOpen(false);
    setActiveViolation(null);
  };

  if (!permit && !loading) return <div className="text-center p-8 mt-20">Permit not found.</div>;


  const verifiedCount = latestReport?.approved_elements?.length || 0;
  const missingCount = latestReport?.violations?.length || 0;

  return (
    <div className="bg-background font-body text-on-surface min-h-screen pb-32">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between px-6 h-16 w-full">
          <div className="flex items-center gap-4">
            <span onClick={() => navigate(`/permit/${id}`)} className="material-symbols-outlined text-slate-900 dark:text-slate-100 cursor-pointer">arrow_back</span>
            <div className="flex items-center gap-2">
              <img src="/scc_logo.jpg" alt="SCC Logo" className="h-6 w-6 object-contain rounded-full bg-white shadow-sm" />
              <h1 className="font-['Inter'] font-bold tracking-tight text-slate-900 dark:text-slate-100 text-base sm:text-xl">Santa Clara County</h1>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="material-symbols-outlined text-slate-500 dark:text-slate-400">notifications</span>
            <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container font-bold text-xs">
                {user?.name?.charAt(0) || user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
          </div>
        </div>
      </header>

      <main className="pt-24 px-6 max-w-md mx-auto">
        {!permit ? (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        ) : (
            <>
                {/* Editorial Header */}
                <div className="mb-10">
                  <span className="text-primary font-bold tracking-[0.15em] text-[10px] uppercase block mb-2">Permit {getDisplayId(permit.id)}</span>
                  <h2 className="text-4xl font-extrabold text-on-surface leading-tight tracking-tighter mb-4">Document Center</h2>
                  <p className="text-tertiary text-sm leading-relaxed">Ensure all structural drawings and site surveys are verified to proceed to architectural review.</p>
                </div>

                {/* Asymmetric Status Summary */}
                <div className="grid grid-cols-2 gap-4 mb-10">
                  <div className="bg-surface-container-low p-5 rounded-2xl flex flex-col justify-between h-32">
                    <span className="material-symbols-outlined text-secondary text-3xl">verified</span>
                    <div>
                      <div className="text-2xl font-black text-on-surface">{verifiedCount.toString().padStart(2, '0')}</div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-tertiary">Verified</div>
                    </div>
                  </div>
                  <div className="bg-primary-container p-5 rounded-2xl flex flex-col justify-between h-32 text-on-primary-container">
                    <span className="material-symbols-outlined text-on-primary-container text-3xl">hourglass_empty</span>
                    <div>
                      <div className="text-2xl font-black">{missingCount.toString().padStart(2, '0')}</div>
                      <div className="text-[10px] font-bold uppercase tracking-widest opacity-80">Pending</div>
                    </div>
                  </div>
                </div>

                {/* Upload Action */}
                <div className="mb-10">
                  <form onSubmit={handleResubmit}>
                    <div className="relative cursor-pointer w-full primary-gradient text-on-primary py-5 rounded-full font-bold flex items-center justify-center gap-3 shadow-lg active:scale-95 transition-all duration-200">
                        {loading ? (
                             <><Loader2 className="w-5 h-5 animate-spin" /> <span>Analyzing...</span></>
                        ) : (
                            <>
                                <span className="material-symbols-outlined">cloud_upload</span>
                                <span>{file ? file.name : 'Upload New Drawing'}</span>
                                <input
                                    type="file"
                                    accept=".pdf"
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                    onChange={handleFileChange}
                                    ref={fileInputRef}
                                />
                            </>
                        )}
                    </div>
                    {error && <p className="mt-2 text-sm text-error text-center font-medium">{error}</p>}
                    {file && !loading && (
                        <div className="mt-4 flex justify-center">
                            <button
                                type="submit"
                                className="bg-primary text-white px-6 py-2 rounded-full text-sm font-bold shadow-md hover:bg-primary/90 transition-colors"
                            >
                                Submit for Analysis
                            </button>
                        </div>
                    )}
                  </form>
                </div>

                {/* Document List (Violations and Approvals) */}
                <div className="space-y-6">
                  <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-tertiary ml-1">Analysis Results</h3>

                  {latestReport?.violations?.map((violation: any, idx: number) => (
                      <div key={`violation-${idx}`} className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm status-bar-missing flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 bg-error-container/30 rounded-xl flex items-center justify-center">
                            <span className="material-symbols-outlined text-error">map</span>
                          </div>
                          <div>
                            <h4 className="font-bold text-on-surface text-sm line-clamp-1">{violation.section}</h4>
                            <p className="text-[10px] text-error font-semibold uppercase">Action Required</p>
                          </div>
                        </div>
                        <button onClick={() => openChatForViolation(violation)} className="bg-surface-container-high p-2 rounded-lg text-primary hover:bg-primary-fixed transition-colors">
                          <span className="material-symbols-outlined text-sm">chat</span>
                        </button>
                      </div>
                  ))}

                  {latestReport?.approved_elements?.map((element: string, idx: number) => (
                      <div key={`approved-${idx}`} className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm status-bar-verified flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 bg-surface-container-low rounded-xl flex items-center justify-center">
                            <span className="material-symbols-outlined text-secondary">architecture</span>
                          </div>
                          <div className="pr-4">
                            <h4 className="font-bold text-on-surface text-sm line-clamp-2">{element}</h4>
                            <p className="text-[10px] text-tertiary font-mono">VERIFIED.PDF</p>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                        </div>
                      </div>
                  ))}

                  {(!latestReport || (!latestReport.violations?.length && !latestReport.approved_elements?.length)) && (
                      <div className="text-center p-6 text-tertiary text-sm">
                          No analysis data available. Please upload a drawing for review.
                      </div>
                  )}
                </div>

                {/* Submission History snippet */}
                {permit.submissions && permit.submissions.length > 0 && (
                    <div className="mt-8 pt-6 border-t border-surface-container">
                        <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-tertiary ml-1 mb-4">Submission History</h3>
                        <div className="space-y-3">
                            {[...permit.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 3).map((sub: any, idx: number) => (
                                <div key={sub.id} className="flex justify-between items-center text-sm p-3 bg-surface-container-low rounded-xl">
                                    <div className="flex flex-col">
                                        <span className="font-bold">v{permit.submissions.length - idx} • {sub.file_name}</span>
                                        <span className="text-[10px] text-tertiary">{new Date(sub.created_at).toLocaleString()}</span>
                                    </div>
                                    <span className="text-[10px] font-bold uppercase px-2 py-1 bg-surface-container-highest rounded-md text-tertiary">{sub.analysis_status}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Sticky Footer Info */}
                <div className="mt-12 p-6 bg-surface-container-highest/50 rounded-3xl text-center">
                  <p className="text-[11px] text-on-surface-variant font-medium">Next Step: Payment of Plan Review Fees</p>
                  <div className="mt-4 flex justify-center gap-1">
                    <div className="w-8 h-1 bg-primary rounded-full"></div>
                    <div className="w-8 h-1 bg-primary rounded-full"></div>
                    <div className="w-8 h-1 bg-primary-fixed rounded-full"></div>
                    <div className="w-8 h-1 bg-primary-fixed rounded-full"></div>
                  </div>
                </div>
            </>
        )}
      </main>

      <BottomNav />

      {/* Chat Side Panel Overlay */}
      {isChatOpen && activeViolation && (
        <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm transition-opacity" onClick={closeChat}></div>

          <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 shadow-2xl">
            <div className="pointer-events-auto w-screen max-w-md transform transition-all">
              <div className="flex h-full flex-col bg-white shadow-xl">
                {/* Header */}
                <div className="bg-primary px-4 py-6 sm:px-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-semibold leading-6 text-white" id="slide-over-title">
                      Chat with Code Agent
                    </h2>
                    <div className="ml-3 flex h-7 items-center">
                      <button
                        type="button"
                        className="relative rounded-md text-primary-fixed hover:text-white focus:outline-none"
                        onClick={closeChat}
                      >
                        <span className="absolute -inset-2.5" />
                        <span className="sr-only">Close panel</span>
                        <X className="h-6 w-6" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-1">
                    <p className="text-sm text-primary-fixed font-mono line-clamp-1">
                      Ref: {activeViolation.section}
                    </p>
                  </div>
                </div>

                {/* Chat Messages */}
                <div className="relative flex-1 px-4 py-6 sm:px-6 overflow-y-auto bg-surface">
                  <div className="space-y-4">
                    {chatMessages.map((msg, index) => (
                      <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`rounded-xl px-4 py-3 max-w-[85%] text-sm shadow-sm ${
                          msg.role === 'user'
                            ? 'bg-primary text-white rounded-tr-sm'
                            : 'bg-white border border-surface-container text-on-surface rounded-tl-sm'
                        }`}>
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="rounded-xl rounded-tl-sm px-4 py-3 bg-white border border-surface-container text-tertiary shadow-sm text-sm flex items-center">
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          Agent is typing...
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Input Area */}
                <div className="flex-shrink-0 border-t border-surface-container px-4 py-4 sm:px-6 bg-white">
                  <form onSubmit={sendChatMessage} className="flex gap-3">
                    <div className="relative flex-grow">
                      <textarea
                        rows={2}
                        className="block w-full rounded-xl border-0 py-3 pl-4 pr-10 text-on-surface ring-1 ring-inset ring-surface-container focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm resize-none outline-none bg-surface"
                        placeholder="Ask about this violation..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={chatLoading}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendChatMessage(e as any);
                          }
                        }}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={!chatInput.trim() || chatLoading}
                      className={`inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors ${
                        !chatInput.trim() || chatLoading ? 'bg-primary-fixed text-primary cursor-not-allowed' : 'bg-primary hover:bg-primary/90'
                      }`}
                    >
                      <Send className="h-5 w-5" aria-hidden="true" />
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}