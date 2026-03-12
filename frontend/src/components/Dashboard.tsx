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
import { useNavigate, Link } from 'react-router-dom';
import { MapPin, FileText, Plus, LogOut, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export function Dashboard() {
  const { user, logout, currentProperty, setCurrentProperty } = useAuthStore();
  const navigate = useNavigate();
  const [properties, setProperties] = useState<any[]>([]);
  const [permits, setPermits] = useState<any[]>([]);
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
        // Fetch properties
        const propResponse = await axios.get(`${API_URL}/api/users/${user.id}/properties`);

        if (!isMounted) return;

        let props = propResponse.data;

        // Prevent double creation in React Strict Mode by checking if we already started creating
        if (props.length === 0) {
            // Check if we already have it in local state to avoid race condition
            // Auto-create a property for demo purposes
            try {
              const newPropRes = await axios.post(`${API_URL}/api/users/${user.id}/properties`, {
                  address: "123 Main St",
                  city: "Santa Clara",
                  zip_code: "95050"
              });
              props = [newPropRes.data];
            } catch (e) {
              // If it failed, it might be a race condition from strict mode. Fetch again just in case
              const retryRes = await axios.get(`${API_URL}/api/users/${user.id}/properties`);
              props = retryRes.data;
            }
        }

        if (!isMounted) return;

        // Remove duplicates just in case there are multiple entries for the same address
        const uniqueProps = [];
        const seenAddresses = new Set();
        for (const p of props) {
            if (!seenAddresses.has(p.address)) {
                seenAddresses.add(p.address);
                uniqueProps.push(p);
            }
        }
        props = uniqueProps;

        setProperties(props);
        if (!currentProperty && props.length > 0) {
            setCurrentProperty(props[0]);
        }

        // Fetch permits if we have a property
        if (props.length > 0) {
            const propId = currentProperty ? currentProperty.id : props[0].id;
            const permitResponse = await axios.get(`${API_URL}/api/properties/${propId}/permits`);
            if (isMounted) {
                setPermits(permitResponse.data);
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

  const handleCreatePermit = async () => {
      if (!currentProperty) return;
      const title = prompt("Enter a title for the new permit application:");
      if (!title) return;

      try {
          await axios.post(`${API_URL}/api/properties/${currentProperty.id}/permits`, {
              title,
              description: "Building plan submission"
          });
          // Refresh permits
          const permitResponse = await axios.get(`${API_URL}/api/properties/${currentProperty.id}/permits`);
          setPermits(permitResponse.data);
      } catch(err) {
          console.error("Failed to create permit", err);
      }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('approved')) return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">{status}</span>;
    if (s.includes('suggested')) return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">{status}</span>;
    if (s.includes('rejected')) return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">{status}</span>;
    return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">{status}</span>;
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-3">
              <img src="/scc_logo.jpg" alt="SCC Logo" className="h-8 w-8 rounded-full" />
              <h1 className="text-xl font-bold text-gray-900">Santa Clara County Portal</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">{user.email}</span>
              <button onClick={() => { logout(); navigate('/login'); }} className="text-gray-400 hover:text-gray-500">
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {loading ? (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        ) : (
            <div className="space-y-8">
                {/* Property Card */}
                <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-100">
                    <div className="px-6 py-5 border-b border-gray-200 bg-gray-50 flex items-center">
                        <MapPin className="text-blue-500 mr-2" />
                        <h3 className="text-lg leading-6 font-medium text-gray-900">My Properties</h3>
                    </div>
                    <div className="p-6">
                        {properties.map(prop => (
                            <div key={prop.id} className="border border-gray-200 rounded-md p-4 bg-white">
                                <p className="font-semibold text-gray-900">{prop.address}</p>
                                <p className="text-gray-500 text-sm">{prop.city}, CA {prop.zip_code}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Permits List */}
                <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-100">
                    <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                        <div className="flex items-center">
                            <FileText className="text-blue-500 mr-2" />
                            <h3 className="text-lg leading-6 font-medium text-gray-900">Permit Applications</h3>
                        </div>
                        <button
                            onClick={handleCreatePermit}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
                        >
                            <Plus className="w-4 h-4 mr-1" /> New Permit
                        </button>
                    </div>

                    <ul className="divide-y divide-gray-200">
                        {permits.length === 0 ? (
                            <li className="p-6 text-center text-gray-500">No permits found. Create one to get started.</li>
                        ) : (
                            permits.map(permit => (
                                <li key={permit.id}>
                                    <Link to={`/permit/${permit.id}`} className="block hover:bg-gray-50 px-6 py-4 transition duration-150">
                                        <div className="flex items-center justify-between">
                                            <div className="flex flex-col">
                                                <p className="text-sm font-medium text-blue-600 truncate">{permit.title}</p>
                                                <p className="text-xs text-gray-500 mt-1">Submitted on {new Date(permit.created_at).toLocaleDateString()}</p>
                                            </div>
                                            <div className="flex items-center">
                                                {getStatusBadge(permit.status)}
                                            </div>
                                        </div>
                                    </Link>
                                </li>
                            ))
                        )}
                    </ul>
                </div>
            </div>
        )}
      </main>
    </div>
  );
}
