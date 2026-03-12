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
import { ArrowLeft, Upload, AlertCircle, CheckCircle2, AlertTriangle, Loader2, Clock, LogOut, Trash2, MessageSquare, X, Send } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export function PermitDetail() {
  const { id } = useParams<{ id: string }>();
  const { user, logout } = useAuthStore();
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

        // Find the latest submission
        if (res.data.submissions && res.data.submissions.length > 0) {
            // Sort by created_at descending
            const sorted = [...res.data.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

            try {
                // Parse the stored JSON string
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
  }, [id, user]);

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

      // Refresh the page data
      const res = await axios.get(`${API_URL}/api/permits/${id}`);
      setPermit(res.data);
      if (res.data.submissions && res.data.submissions.length > 0) {
          const sorted = [...res.data.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
          setLatestReport(JSON.parse(sorted[0].report_json));
      }

      // Crucial fix: Reset the file input so it correctly updates UI state and allows re-selection
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

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved': return 'text-green-600 bg-green-50 border-green-200';
      case 'changes suggested': return 'text-amber-600 bg-amber-50 border-amber-200';
      case 'rejected': return 'text-red-600 bg-red-50 border-red-200';
      case 'draft': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved': return <CheckCircle2 className="w-6 h-6 text-green-600" />;
      case 'changes suggested': return <AlertTriangle className="w-6 h-6 text-amber-600" />;
      case 'rejected': return <AlertCircle className="w-6 h-6 text-red-600" />;
      default: return null;
    }
  };

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this permit? This action cannot be undone.")) {
      try {
        await axios.delete(`${API_URL}/api/permits/${id}`);
        navigate('/');
      } catch (err) {
        console.error("Failed to delete permit", err);
        alert("Failed to delete permit");
      }
    }
  };

  const openChatForViolation = (violation: any) => {
    setActiveViolation(violation);
    setChatMessages([
      {
        role: "assistant",
        content: `Hi there! You're asking about the violation for section ${violation.section}. How can I help you?`
      }
    ]);

    // Auto-fill chat input with violation details as requested
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

  if (!permit) return <div className="flex justify-center mt-20"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigate('/')}>
              <img src="/scc_logo.jpg" alt="SCC Logo" className="h-8 w-8 rounded-full" />
              <h1 className="text-xl font-bold text-gray-900">Santa Clara County Portal</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">{user?.email}</span>
              <button onClick={() => { logout(); navigate('/login'); }} className="text-gray-400 hover:text-gray-500">
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex justify-between items-center">
            <button onClick={() => navigate('/')} className="flex items-center text-sm font-medium text-gray-500 hover:text-gray-700">
                <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
            </button>
            <button onClick={handleDelete} className="flex items-center text-sm font-medium text-red-500 hover:text-red-700">
                <Trash2 className="w-4 h-4 mr-1" /> Delete Permit
            </button>
        </div>

        <div className="bg-white shadow-sm rounded-xl overflow-hidden border border-gray-100 p-6">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">{permit.title}</h2>
                    <p className="text-sm text-gray-500 mt-1">Status: <span className="font-semibold text-gray-700">{permit.status}</span></p>
                </div>
                <div className="flex items-center text-sm text-gray-500">
                    <Clock className="w-4 h-4 mr-1" />
                    Created: {new Date(permit.created_at).toLocaleDateString()}
                </div>
            </div>

            {/* Upload Section (Resubmit) */}
            <form onSubmit={handleResubmit} className="bg-gray-50 p-6 rounded-lg border border-gray-200 mb-8">
                <h3 className="text-md font-medium text-gray-900 mb-4 flex items-center">
                    <Upload className="w-4 h-4 mr-2 text-blue-500" />
                    {permit.status === 'Draft' ? 'Upload Initial Plan PDF' : 'Upload Revised Plan PDF (Re-analysis)'}
                </h3>

                <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-xl hover:border-blue-400 bg-white">
                    <div className="space-y-2 text-center">
                        <div className="flex text-sm text-gray-600 justify-center">
                            <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                            <span>{file ? file.name : 'Select a PDF file'}</span>
                            <input
                                type="file"
                                accept=".pdf"
                                className="sr-only"
                                onChange={handleFileChange}
                                ref={fileInputRef}
                            />
                            </label>
                        </div>
                    </div>
                </div>

                {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

                <button
                    type="submit"
                    disabled={!file || loading}
                    className={`mt-4 w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white ${
                    !file || loading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                >
                    {loading ? <span className="flex items-center"><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Analyzing...</span> : 'Submit & Analyze'}
                </button>
            </form>

            {/* Results Section */}
            {latestReport && (
            <div className="border border-gray-200 rounded-xl overflow-hidden mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className={`px-6 py-4 border-b flex items-center space-x-3 ${getStatusColor(latestReport.status)}`}>
                    {getStatusIcon(latestReport.status)}
                    <h2 className="text-lg font-bold">Latest Analysis: {latestReport.status}</h2>
                </div>

                <div className="p-6 space-y-8 bg-white">
                {/* Violations */}
                {latestReport.violations && latestReport.violations.length > 0 && (
                    <div>
                    <h3 className="text-md font-semibold text-gray-900 mb-4 flex items-center">
                        <AlertTriangle className="w-5 h-5 text-amber-500 mr-2" /> Required Changes & Violations
                    </h3>
                    <div className="space-y-4">
                        {latestReport.violations.map((violation: any, index: number) => (
                        <div key={index} className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                            <div className="font-semibold text-amber-900 mb-1 font-mono text-xs bg-amber-100 inline-block px-2 py-1 rounded">
                            {violation.section}
                            </div>
                            <p className="text-gray-800 text-sm font-medium mb-2">{violation.description}</p>
                            <div className="bg-white bg-opacity-60 rounded p-2 text-xs text-gray-700 mb-2">
                            <strong>Suggestion:</strong> {violation.suggestion}
                            </div>
                            <button
                                onClick={() => openChatForViolation(violation)}
                                className="inline-flex items-center text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-full transition-colors"
                            >
                                <MessageSquare className="w-3.5 h-3.5 mr-1.5" />
                                Ask Agent
                            </button>
                        </div>
                        ))}
                    </div>
                    </div>
                )}

                {/* Approved Elements */}
                {latestReport.approved_elements && latestReport.approved_elements.length > 0 && (
                    <div>
                    <h3 className="text-md font-semibold text-gray-900 mb-3 flex items-center">
                        <CheckCircle2 className="w-5 h-5 text-green-500 mr-2" /> Compliant Elements
                    </h3>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {latestReport.approved_elements.map((element: string, index: number) => (
                        <li key={index} className="flex items-start text-sm">
                            <CheckCircle2 className="w-4 h-4 text-green-400 mr-2 flex-shrink-0 mt-0.5" />
                            <span className="text-gray-700">{element}</span>
                        </li>
                        ))}
                    </ul>
                    </div>
                )}
                </div>
            </div>
            )}
        </div>

        {/* History Section */}
        {permit.submissions && permit.submissions.length > 1 && (
            <div className="bg-white shadow-sm rounded-xl border border-gray-100 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Submission History</h3>
                <ul className="space-y-4">
                    {[...permit.submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map((sub: any, idx: number) => (
                        <li key={sub.id} className="text-sm border-l-2 border-gray-200 pl-4 py-1">
                            <p className="font-medium text-gray-900">Submission #{permit.submissions.length - idx} <span className="text-gray-500 font-normal">({new Date(sub.created_at).toLocaleString()})</span></p>
                            <p className="text-gray-600 mt-1">File: {sub.file_name}</p>
                            <p className="text-gray-600">Status: <span className="font-medium">{sub.analysis_status}</span></p>
                        </li>
                    ))}
                </ul>
            </div>
        )}
      </main>

      {/* Chat Side Panel Overlay */}
      {isChatOpen && activeViolation && (
        <div className="fixed inset-0 z-50 overflow-hidden pointer-events-none" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
          {/* Removed the solid background overlay to allow viewing the permit details */}

          <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 shadow-2xl">
            <div className="pointer-events-auto w-screen max-w-md transform transition-all">
              <div className="flex h-full flex-col bg-white shadow-xl">
                {/* Header */}
                <div className="bg-blue-600 px-4 py-6 sm:px-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-semibold leading-6 text-white" id="slide-over-title">
                      Chat with Code Agent
                    </h2>
                    <div className="ml-3 flex h-7 items-center">
                      <button
                        type="button"
                        className="relative rounded-md text-blue-200 hover:text-white focus:outline-none focus:ring-2 focus:ring-white"
                        onClick={closeChat}
                      >
                        <span className="absolute -inset-2.5" />
                        <span className="sr-only">Close panel</span>
                        <X className="h-6 w-6" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-1">
                    <p className="text-sm text-blue-100 font-mono">
                      Ref: {activeViolation.section}
                    </p>
                  </div>
                </div>

                {/* Chat Messages */}
                <div className="relative flex-1 px-4 py-6 sm:px-6 overflow-y-auto bg-gray-50">
                  <div className="space-y-4">
                    {chatMessages.map((msg, index) => (
                      <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`rounded-lg px-4 py-2 max-w-[85%] text-sm ${
                          msg.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                        }`}>
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="rounded-lg px-4 py-2 bg-white border border-gray-200 text-gray-500 shadow-sm text-sm flex items-center">
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          Agent is typing...
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Input Area */}
                <div className="flex-shrink-0 border-t border-gray-200 px-4 py-4 sm:px-6 bg-white">
                  <form onSubmit={sendChatMessage} className="flex space-x-3">
                    <div className="relative flex-grow">
                      <textarea
                        rows={3}
                        className="block w-full rounded-md border-0 py-2 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 resize-none"
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
                      className={`inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
                        !chatInput.trim() || chatLoading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500'
                      }`}
                    >
                      <Send className="h-4 w-4" aria-hidden="true" />
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
