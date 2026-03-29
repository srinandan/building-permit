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
import { useNavigate } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Loader2 } from 'lucide-react';

const API_URL = '';

export function Dashboard() {
  const { user, currentProperty, setCurrentProperty, logout } = useAuthStore();
  const navigate = useNavigate();

  const [permits, setPermits] = useState<any[]>([]);

  const handleDeletePermit = async (permitId: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigating to detail page
    if (window.confirm('Are you sure you want to delete this permit application?')) {
      try {
        await axios.delete(`${API_URL}/api/permits/${permitId}`);
        setPermits(permits.filter((p) => p.id !== permitId));
      } catch (error) {
        console.error('Failed to delete permit', error);
      }
    }
  };
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    let isMounted = true;

    const fetchData = async () => {
      setLoading(true);
      try {
        const propResponse = await axios.get(`${API_URL}/api/users/${user.id}/properties`);
        if (!isMounted) return;

        let props = propResponse.data;

        if (props.length === 0) {
            try {
              const newPropRes = await axios.post(`${API_URL}/api/users/${user.id}/properties`, {
                  address: "123 Main St",
                  city: "San Paloma",
                  zip_code: "95050"
              });
              props = [newPropRes.data];
            } catch (e) {
              const retryRes = await axios.get(`${API_URL}/api/users/${user.id}/properties`);
              props = retryRes.data;
            }
        }

        if (!isMounted) return;

        const uniqueProps = [];
        const seenAddresses = new Set();
        for (const p of props) {
            if (!seenAddresses.has(p.address)) {
                seenAddresses.add(p.address);
                uniqueProps.push(p);
            }
        }
        props = uniqueProps;

        if (!currentProperty && props.length > 0) {
            setCurrentProperty(props[0]);
        }

        if (props.length > 0) {
            try {
                const permitPromises = props.map(async (prop: any) => {
                    const permitResponse = await axios.get(`${API_URL}/api/properties/${prop.id}/permits`);
                    const permitsData = Array.isArray(permitResponse.data) ? permitResponse.data : [];
                    return permitsData.map(p => ({
                        ...p,
                        propertyAddress: prop.address,
                        propertyCity: prop.city
                    }));
                });

                const results = await Promise.allSettled(permitPromises);

                let allPermits: any[] = [];
                results.forEach(result => {
                    if (result.status === 'fulfilled') {
                        allPermits = [...allPermits, ...result.value];
                    } else {
                        console.error("Failed fetching some permits", result.reason);
                    }
                });

                // Sort by created_at descending (newest first)
                allPermits.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

                if (isMounted) {
                    setPermits(allPermits);
                }
            } catch (err) {
                console.error("Error aggregating permits", err);
            }
        }

      } catch (err) {
        if (isMounted) console.error("Failed fetching data", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [user, currentProperty, setCurrentProperty, navigate]);

  const getStatusColorClass = (status: string) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('approved')) return 'bg-secondary';
    if (s.includes('review')) return 'bg-primary';
    if (s.includes('suggested') || s.includes('action') || s.includes('draft') || s.includes('rejected')) return 'bg-error';
    return 'bg-outline'; // Default fallback
  };

  const getStatusLabel = (status: string) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('approved')) return 'Approved';
    if (s.includes('review')) return 'In Review';
    return 'Action Required';
  };

  const getStatusLabelStyles = (status: string) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('approved')) return 'bg-secondary-container text-on-secondary-container';
    if (s.includes('review')) return 'bg-primary-fixed text-on-primary-fixed-variant';
    return 'bg-error-container text-on-error-container';
  };

  const getTimeAgo = (dateStr: string) => {
    const now = new Date();
    const date = new Date(dateStr);
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return `${diffInSeconds} seconds ago`;
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes} minutes ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) return `${diffInDays} days ago`;

    // Fallback to formatted date
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const approvedCount = permits.filter(p => p.status?.toLowerCase().includes('approved')).length;
  const inReviewCount = permits.filter(p => p.status?.toLowerCase().includes('review')).length;

  // Create a display ID to fake the #BP-2024-XXXX format based on real DB IDs
  const getDisplayId = (id: number) => {
    return `#BP-2024-${String(id).padStart(4, '0')}`;
  };

  if (!user) return null;

  return (
    <div className="bg-surface font-body text-on-surface antialiased pb-28 min-h-screen">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between px-6 h-16 w-full">
          <div className="flex items-center gap-4">
            <button className="text-blue-700 dark:text-blue-400 active:scale-95 duration-200">
              <span className="material-symbols-outlined">menu</span>
            </button>
            <div className="flex items-center gap-2">
              <img src="/spc_logo.png" alt="San Paloma County Permit Hub Logo" className="h-8 w-8 object-contain rounded-full bg-white shadow-sm" />
              <h1 className="text-sm sm:text-base md:text-xl leading-tight font-black text-blue-800 dark:text-blue-400 tracking-tight font-['Inter']">
                San Paloma County Permit Hub
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="text-slate-500 dark:text-slate-400 p-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors rounded-full active:scale-95 duration-200">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <button
                onClick={() => {
                    logout();
                    navigate('/login');
                }}
                className="text-slate-500 dark:text-slate-400 p-2 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition-colors rounded-full active:scale-95 duration-200"
                aria-label="Sign Out"
                title="Sign Out"
            >
              <span className="material-symbols-outlined">logout</span>
            </button>
          </div>
        </div>
      </header>

      <main className="pt-20 px-6">
        {loading ? (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        ) : (
            <>
                {/* Hero Section & CTA */}
                <section className="py-6">
                  <div className="flex flex-col gap-2 mb-8">
                    <h2 className="text-4xl font-extrabold tracking-tighter text-on-surface leading-tight">Welcome back, <span className="text-primary">{user.name || user.email.split('@')[0]}</span></h2>
                    <p className="text-on-surface-variant font-medium">You have {permits.length} active permit applications needing attention.</p>
                  </div>
                  <button
                    onClick={() => navigate('/new-permit')}
                    className="w-full primary-gradient text-on-primary py-5 px-6 rounded-xl flex items-center justify-between shadow-lg shadow-primary/20 active:scale-95 transition-transform duration-200"
                  >
                    <span className="text-lg font-bold tracking-tight">Start New Application</span>
                    <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>add_circle</span>
                  </button>
                </section>

                {/* Search Bar */}
                <section className="mb-10">
                  <div className="relative ghost-border rounded-xl bg-surface-container-low px-4 py-3 flex items-center gap-3">
                    <span className="material-symbols-outlined text-outline">search</span>
                    <input className="bg-transparent border-none focus:ring-0 text-on-surface-variant w-full font-medium placeholder:text-outline outline-none" placeholder="Search permits by ID or address..." type="text"/>
                    <span className="material-symbols-outlined text-outline">tune</span>
                  </div>
                </section>

                {/* Bento Stats Grid */}
                <section className="grid grid-cols-2 gap-4 mb-10">
                  <div className="bg-surface-container-lowest p-5 rounded-xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[11px] font-bold uppercase tracking-widest text-tertiary">Approved</span>
                    <span className="text-3xl font-black text-secondary">{approvedCount.toString().padStart(2, '0')}</span>
                  </div>
                  <div className="bg-surface-container-lowest p-5 rounded-xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[11px] font-bold uppercase tracking-widest text-tertiary">In Review</span>
                    <span className="text-3xl font-black text-primary">{inReviewCount.toString().padStart(2, '0')}</span>
                  </div>
                </section>

                {/* Permit Cards */}
                <section className="flex flex-col gap-6 mb-12">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold uppercase tracking-[0.15em] text-tertiary">Active Permits</h3>
                    <span className="text-xs font-bold text-primary cursor-pointer">View All</span>
                  </div>

                  {permits.length === 0 ? (
                      <div className="text-center p-8 bg-surface-container-lowest rounded-xl shadow-sm text-on-surface-variant">
                          No active permits found. Start a new application!
                      </div>
                  ) : (
                      permits.map(permit => (
                          <div
                            key={permit.id}
                            onClick={() => navigate(`/permit/${permit.id}`)}
                            className="bg-surface-container-lowest rounded-xl overflow-hidden relative shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                          >
                            <div className={`absolute left-0 top-0 bottom-0 w-1 ${getStatusColorClass(permit.status)}`}></div>
                            <div className="p-6">
                              <div className="flex justify-between items-start mb-4">
                                <div className="flex flex-col pr-2">
                                  <span className="text-[10px] font-mono font-bold text-tertiary mb-1">ID: {getDisplayId(permit.id)}</span>
                                  <h4 className="text-lg font-bold text-on-surface line-clamp-1">{permit.title}</h4>
                                </div>
                                <div className="flex flex-col items-end gap-2">
                                  <span className={`shrink-0 px-3 py-1 text-[10px] font-bold rounded-full uppercase tracking-wider ${getStatusLabelStyles(permit.status)}`}>
                                    {getStatusLabel(permit.status)}
                                  </span>
                                  <button
                                    onClick={(e) => handleDeletePermit(permit.id, e)}
                                    className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors active:scale-95 duration-200"
                                    title="Delete Permit"
                                  >
                                    <span className="material-symbols-outlined text-sm">delete</span>
                                  </button>
                                </div>
                              </div>

                              <div className="flex items-center gap-2 text-on-surface-variant mb-4">
                                <span className="material-symbols-outlined text-sm">location_on</span>
                                <span className="text-sm font-medium line-clamp-1">
                                    {permit.propertyAddress ? `${permit.propertyAddress}, ${permit.propertyCity}` : 'No Address Set'}
                                </span>
                              </div>

                              <div className="flex items-center justify-between pt-4 border-t border-surface-container">
                                <div className="flex flex-col">
                                  <span className="text-[10px] uppercase font-bold text-outline tracking-wider">Last Update</span>
                                  <span className="text-xs font-semibold text-on-surface">{getTimeAgo(permit.created_at)}</span>
                                </div>
                                <button
                                    className={`px-4 py-2 rounded-lg text-xs font-bold active:scale-95 duration-150 ${
                                        permit.status?.toLowerCase().includes('approved') ? 'bg-secondary text-on-secondary' :
                                        'bg-surface-container-high text-on-surface'
                                    }`}
                                >
                                    {permit.status?.toLowerCase().includes('approved') ? 'Download' :
                                     permit.status?.toLowerCase().includes('review') ? 'View Details' : 'Fix Issues'}
                                </button>
                              </div>
                            </div>
                          </div>
                      ))
                  )}
                </section>
            </>
        )}
      </main>

      <BottomNav />
    </div>
  );
}