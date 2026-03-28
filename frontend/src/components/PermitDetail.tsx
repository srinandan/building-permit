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

import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store';
import { useParams, useNavigate } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Loader2 } from 'lucide-react';

const API_URL = '';

export function PermitDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [permit, setPermit] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this permit application?')) {
      try {
        await axios.delete(`${API_URL}/api/permits/${id}`);
        navigate('/');
      } catch (error) {
        console.error('Failed to delete permit', error);
      }
    }
  };

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    const fetchPermit = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_URL}/api/permits/${id}`);
        setPermit(res.data);
      } catch (err) {
        console.error("Failed fetching permit", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPermit();
  }, [id, user, navigate]);

  const getDisplayId = (id: number) => {
    return `PRMT-2024-${String(id).padStart(4, '0')}`;
  };

  const getStatusLabelStyles = (status: string) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('approved')) return 'bg-secondary-container text-on-secondary-container';
    if (s.includes('review')) return 'bg-primary-fixed text-on-primary-fixed-variant';
    if (s.includes('suggested') || s.includes('action') || s.includes('draft') || s.includes('rejected')) return 'bg-error-container text-on-error-container';
    return 'bg-surface-container-highest text-on-surface-variant';
  };

  const formatDateTime = (dateStr: string) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' • ' +
             date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  if (!user) return null;

  return (
    <div className="bg-surface font-body text-on-surface antialiased pb-32 min-h-screen">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between px-6 h-16 w-full">
          <div className="flex items-center gap-4">
            <button
                onClick={() => navigate('/')}
                className="active:scale-95 duration-200 text-slate-900"
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <div className="flex items-center gap-2">
              <img src="/spc_logo.png" alt="San Paloma County Permit Hub Logo" className="h-6 w-6 object-contain rounded-full bg-white shadow-sm" />
              <h1 className="font-['Inter'] font-bold tracking-tight text-slate-900 dark:text-slate-100 text-xs sm:text-sm md:text-lg leading-tight">San Paloma County Permit Hub</h1>
            </div>
          </div>
          <div className="flex gap-4">
            <button
              onClick={handleDelete}
              className="material-symbols-outlined text-slate-500 hover:text-red-600 transition-colors"
              title="Delete Permit"
            >
              delete
            </button>
            <span className="material-symbols-outlined text-slate-500 cursor-pointer hover:text-slate-800">share</span>
            <span className="material-symbols-outlined text-slate-500 cursor-pointer hover:text-slate-800">notifications</span>
          </div>
        </div>
      </header>

      <main className="pt-20 px-6 max-w-lg mx-auto">
        {loading ? (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        ) : permit ? (
            <>
                {/* Hero Header Section */}
                <section className="mb-10">
                  <div className="flex flex-col gap-1">
                    <span className="text-[11px] font-bold uppercase tracking-[0.15rem] text-primary">Application ID</span>
                    <h2 className="text-4xl font-black tracking-tighter text-on-surface leading-none">{getDisplayId(permit.id)}</h2>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${getStatusLabelStyles(permit.status)}`}>
                        {permit.status || 'Draft'}
                      </span>
                      <span className="text-xs text-tertiary font-medium">{permit.title}</span>
                    </div>
                  </div>
                </section>

                {/* Progress Tracker (Architectural Step Layout) */}
                <section className="mb-10">
                  <div className="bg-surface-container-low rounded-3xl p-6 relative overflow-hidden">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-tertiary mb-6">Review Timeline</h3>
                    <div className="relative flex flex-col gap-8">
                      {/* Vertical Line */}
                      <div className="absolute left-[15px] top-2 bottom-2 w-[2px] bg-primary-fixed"></div>
                      {/* Dynamically size the active line based on status */}
                      <div className={`absolute left-[15px] top-2 w-[2px] bg-primary transition-all duration-500 ${
                          permit.status?.toLowerCase().includes('approved') ? 'h-full' :
                          permit.status?.toLowerCase().includes('review') ? 'h-1/3' :
                          permit.status?.toLowerCase().includes('draft') ? 'h-0' : 'h-2/3'
                      }`}></div>

                      {/* Step 1 */}
                      <div className="flex gap-6 relative">
                        <div className="z-10 w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white">
                          <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 0, 'wght' 700" }}>check</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-on-surface">Submitted</span>
                          <span className="text-xs text-tertiary">{formatDateTime(permit.created_at)}</span>
                        </div>
                      </div>

                      {/* Step 2 (In Review or beyond) */}
                      <div className={`flex gap-6 relative ${permit.status?.toLowerCase() === 'draft' ? 'opacity-50' : ''}`}>
                        <div className={`z-10 w-8 h-8 rounded-full flex items-center justify-center ${
                            permit.status?.toLowerCase() !== 'draft' ? 'bg-primary text-white' : 'bg-primary-fixed text-on-primary-fixed'
                        }`}>
                          {permit.status?.toLowerCase() !== 'draft' && !permit.status?.toLowerCase().includes('review') ? (
                              <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 0, 'wght' 700" }}>check</span>
                          ) : permit.status?.toLowerCase().includes('review') ? (
                              <div className="w-2 h-2 rounded-full bg-white"></div>
                          ) : (
                              <span className="material-symbols-outlined text-sm">hourglass_empty</span>
                          )}
                        </div>
                        <div className="flex flex-col">
                          <span className={`text-sm font-bold ${permit.status?.toLowerCase().includes('review') ? 'text-primary' : 'text-on-surface'}`}>Under Review</span>
                          <span className="text-xs text-tertiary">
                              {permit.submissions && permit.submissions.length > 0
                                  ? formatDateTime(permit.submissions[permit.submissions.length - 1].created_at)
                                  : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* Step 3 (Action Required / Changes Suggested) */}
                      <div className={`flex gap-6 relative ${
                          !permit.status?.toLowerCase().includes('suggested') &&
                          !permit.status?.toLowerCase().includes('action') &&
                          !permit.status?.toLowerCase().includes('rejected') &&
                          !permit.status?.toLowerCase().includes('approved') ? 'opacity-50 hidden' : ''
                      }`}>
                        <div className={`z-10 w-8 h-8 rounded-full flex items-center justify-center ${
                            permit.status?.toLowerCase().includes('approved') ? 'bg-primary text-white' : 'bg-surface-container-lowest border-4 border-error'
                        }`}>
                            {permit.status?.toLowerCase().includes('approved') ? (
                                <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 0, 'wght' 700" }}>check</span>
                            ) : (
                                <div className="w-2 h-2 rounded-full bg-error"></div>
                            )}
                        </div>
                        <div className="flex flex-col">
                          <span className={`text-sm font-bold ${permit.status?.toLowerCase().includes('approved') ? 'text-on-surface' : 'text-error'}`}>
                              {permit.status?.toLowerCase().includes('approved') ? 'Review Complete' : 'Comments Received'}
                          </span>
                          <span className="text-xs text-tertiary">
                              {permit.submissions && permit.submissions.length > 0
                                  ? formatDateTime(permit.submissions[0].created_at)
                                  : 'Pending'}
                          </span>
                          {!permit.status?.toLowerCase().includes('approved') && permit.submissions && permit.submissions.length > 0 && (
                              <p className="mt-2 text-sm text-on-surface-variant leading-relaxed bg-surface-container-high/50 p-4 rounded-xl">
                                  Action is required on your recent plan submission. Please review the specific code violations and resubmit.
                              </p>
                          )}
                        </div>
                      </div>

                      {/* Step 4 (Final Approval) */}
                      <div className={`flex gap-6 relative ${permit.status?.toLowerCase().includes('approved') ? '' : 'opacity-50'}`}>
                        <div className={`z-10 w-8 h-8 rounded-full flex items-center justify-center ${
                            permit.status?.toLowerCase().includes('approved') ? 'bg-secondary text-white' : 'bg-primary-fixed text-on-primary-fixed'
                        }`}>
                          <span className="material-symbols-outlined text-sm">{permit.status?.toLowerCase().includes('approved') ? 'verified' : 'lock'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className={`text-sm font-bold ${permit.status?.toLowerCase().includes('approved') ? 'text-secondary' : 'text-on-surface'}`}>Final Approval</span>
                          <span className="text-xs text-tertiary">{permit.status?.toLowerCase().includes('approved') ? 'Complete' : 'Pending action'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Documents Navigation Card */}
                <section className="mb-10">
                    <div
                        onClick={() => navigate(`/permit/${id}/documents`)}
                        className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-surface-container-high flex justify-between items-center cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98]"
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-primary-container text-on-primary-container rounded-xl flex items-center justify-center">
                                <span className="material-symbols-outlined">folder_open</span>
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-on-surface">Document Center</h3>
                                <p className="text-xs text-on-surface-variant">View analysis, required changes & upload files</p>
                            </div>
                        </div>
                        <span className="material-symbols-outlined text-outline">chevron_right</span>
                    </div>
                </section>

                {/* Assigned Official */}
                <section className="mb-10">
                  <div className="bg-primary p-8 rounded-[2rem] text-white flex flex-col gap-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-10 -mt-10 blur-3xl"></div>
                    <div className="flex flex-col gap-1">
                      <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-80">Assigned Official</h3>
                      <span className="text-2xl font-bold tracking-tight">Marcus Thorne</span>
                      <span className="text-xs opacity-80">Senior Structural Reviewer</span>
                    </div>
                    <div className="flex gap-4">
                      <button className="flex-1 bg-white/20 hover:bg-white/30 backdrop-blur-md h-12 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95">
                        <span className="material-symbols-outlined text-lg">mail</span>
                        <span className="text-xs font-bold uppercase tracking-wider">Email</span>
                      </button>
                      <button className="flex-1 bg-white/20 hover:bg-white/30 backdrop-blur-md h-12 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95">
                        <span className="material-symbols-outlined text-lg">call</span>
                        <span className="text-xs font-bold uppercase tracking-wider">Call</span>
                      </button>
                    </div>
                  </div>
                </section>

                {/* Technical Codes Accents */}
                <section className="mb-4 text-center">
                  <span className="font-mono text-[10px] text-tertiary uppercase tracking-widest opacity-40">Section 402.1.2 • Structural Integrity Protocol</span>
                </section>
            </>
        ) : (
            <div className="text-center p-8 text-on-surface-variant">Permit not found.</div>
        )}
      </main>

      <BottomNav />
    </div>
  );
}