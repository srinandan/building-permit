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

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store';
import { useNavigate } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Loader2 } from 'lucide-react';
import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';

const API_URL = '';

export function Profile() {
  const { user, currentProperty, setCurrentProperty, logout } = useAuthStore();
  const navigate = useNavigate();

  const [properties, setProperties] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newAddress, setNewAddress] = useState('');
  const [mapCenter, setMapCenter] = useState<{lat: number, lng: number} | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [savingProperty, setSavingProperty] = useState(false);

  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
  });

  const fetchProperties = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/users/${user.id}/properties`);
      const uniqueProps = [];
      const seenAddresses = new Set();
      for (const p of res.data) {
          if (!seenAddresses.has(p.address)) {
              seenAddresses.add(p.address);
              uniqueProps.push(p);
          }
      }
      setProperties(uniqueProps);
    } catch (err) {
      console.error("Failed to load properties:", err);
      setError("Failed to load properties.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleDeleteProperty = async (propertyId: number) => {
    if (window.confirm('Are you sure you want to remove this property?')) {
      try {
        await axios.delete(`${API_URL}/api/properties/${propertyId}`);
        // If we deleted the currently selected property, reset it
        if (currentProperty?.id === propertyId) {
            setCurrentProperty(null);
        }
        await fetchProperties();
      } catch (err) {
        console.error("Failed to delete property:", err);
        setError("Failed to delete property.");
      }
    }
  };

  const handleSearchAddress = async () => {
    if (!newAddress.trim()) return;
    setIsSearching(true);
    setMapError(null);
    setMapCenter(null);

    try {
      const mapRes = await axios.post(`${API_URL}/api/map/search`, { address: newAddress });

      if (mapRes.data && mapRes.data.places && mapRes.data.places.length > 0) {
        const location = mapRes.data.places[0].location;
        if (location) {
           setMapCenter({
             lat: location.latitude,
             lng: location.longitude
           });
        } else {
           setMapError("LOCATION_NOT_FOUND");
        }
      } else {
         setMapError("NO_PLACES_FOUND");
      }
    } catch (err) {
      console.error("Failed to fetch map data:", err);
      setMapError("API_ERROR");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSaveProperty = async () => {
    if (!newAddress.trim() || !user?.id) return;
    setSavingProperty(true);
    try {
        await axios.post(`${API_URL}/api/users/${user.id}/properties`, {
            address: newAddress,
            city: '',
            zip_code: ''
        });
        setNewAddress('');
        setMapCenter(null);
        await fetchProperties();
    } catch (err) {
        console.error("Failed to save property:", err);
        setError("Failed to save property.");
    } finally {
        setSavingProperty(false);
    }
  };


  if (!user) return null;

  return (
    <div className="bg-surface font-body text-on-surface antialiased pb-28 min-h-screen">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between px-6 h-16 w-full">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-black text-slate-800 dark:text-slate-100 tracking-tight font-['Inter']">
              Profile
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button
                onClick={() => {
                    logout();
                    navigate('/login');
                }}
                className="flex items-center gap-1.5 text-sm font-bold text-red-600 dark:text-red-400 py-1.5 px-3 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors rounded-xl active:scale-95 duration-200"
                aria-label="Sign Out"
            >
              <span className="material-symbols-outlined text-[18px]">logout</span>
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="pt-20 px-6 max-w-lg mx-auto">
        {/* User Info */}
        <section className="mb-10 bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-surface-container-high flex flex-col gap-4">
            <div className="flex items-center gap-4 mb-2">
                <div className="w-16 h-16 bg-primary-container text-primary rounded-full flex items-center justify-center text-2xl font-bold uppercase">
                    {user.name ? user.name.charAt(0) : user.email.charAt(0)}
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-on-surface">{user.name || 'User'}</h2>
                    <p className="text-sm text-on-surface-variant">{user.email}</p>
                </div>
            </div>

            <button
                onClick={() => {
                    logout();
                    navigate('/login');
                }}
                className="w-full flex items-center justify-center gap-2 bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 py-3 rounded-xl font-bold text-sm hover:bg-red-100 dark:hover:bg-red-900/40 active:scale-95 transition-all duration-200 border border-red-100 dark:border-red-900/30"
            >
                <span className="material-symbols-outlined text-[20px]">logout</span>
                Sign Out
            </button>
        </section>

        {/* Existing Properties */}
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase tracking-[0.15em] text-tertiary">My Properties</h3>
          </div>

          {error && (
              <div className="mb-4 p-4 bg-error-container text-on-error-container rounded-xl text-sm font-medium">
                  {error}
              </div>
          )}

          {loading ? (
             <div className="flex justify-center p-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
             </div>
          ) : properties.length === 0 ? (
              <div className="text-center p-8 bg-surface-container-lowest rounded-xl shadow-sm text-on-surface-variant">
                  You have no properties saved yet.
              </div>
          ) : (
              <div className="flex flex-col gap-4">
                  {properties.map(property => (
                      <div key={property.id} className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container-high flex justify-between items-center">
                          <div className="flex flex-col pr-4">
                             <span className="font-semibold text-on-surface">{property.address}</span>
                             {(property.city || property.zip_code) && (
                                 <span className="text-xs text-on-surface-variant">
                                     {property.city}{property.city && property.zip_code ? ', ' : ''}{property.zip_code}
                                 </span>
                             )}
                          </div>
                          <button
                              onClick={() => handleDeleteProperty(property.id)}
                              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors active:scale-95 duration-200 flex-shrink-0"
                              title="Remove Property"
                          >
                              <span className="material-symbols-outlined text-sm">delete</span>
                          </button>
                      </div>
                  ))}
              </div>
          )}
        </section>

        {/* Add New Property */}
        <section className="mb-10 bg-surface-container-low p-6 rounded-2xl">
          <h3 className="text-sm font-bold uppercase tracking-[0.15em] text-tertiary mb-4">Add New Property</h3>

          <div className="space-y-4">
             <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">Street Address</label>
                <div className="flex gap-2">
                    <input
                        value={newAddress}
                        onChange={(e) => setNewAddress(e.target.value)}
                        className="flex-1 bg-surface-container-lowest border-none rounded-xl py-3 px-4 text-sm text-on-surface focus:ring-2 focus:ring-primary shadow-sm outline-none"
                        placeholder="123 Main St"
                        type="text"
                    />
                    <button
                        onClick={handleSearchAddress}
                        disabled={isSearching || !newAddress.trim()}
                        className="bg-secondary text-on-secondary px-4 py-3 rounded-xl font-bold text-sm shadow-sm active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                    </button>
                </div>
             </div>

             {/* Map Preview */}
             {(mapCenter || mapError || isSearching) && (
                <div className="mt-4 rounded-xl overflow-hidden shadow-inner bg-surface-container-lowest h-[200px] relative border border-outline-variant/30">
                    {mapError ? (
                        <div className="absolute inset-0 flex items-center justify-center bg-surface-container p-4 text-center">
                            <span className="text-sm text-on-surface-variant">Unable to locate address on map. You can still save it.</span>
                        </div>
                    ) : isSearching || !isLoaded ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-on-surface-variant">
                          <Loader2 className="w-8 h-8 animate-spin mb-2" />
                          <span className="text-sm font-medium">Loading Map...</span>
                        </div>
                    ) : mapCenter ? (
                        <GoogleMap
                          mapContainerStyle={{ width: '100%', height: '200px' }}
                          center={mapCenter}
                          zoom={17}
                          options={{
                            disableDefaultUI: true,
                            zoomControl: true,
                          }}
                        >
                           <Marker position={mapCenter} />
                        </GoogleMap>
                    ) : null}
                 </div>
             )}

             <button
                onClick={handleSaveProperty}
                disabled={savingProperty || !newAddress.trim()}
                className="w-full mt-4 bg-primary text-white py-3 rounded-xl font-bold tracking-wide shadow-md active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
             >
                {savingProperty ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Property'}
             </button>
          </div>
        </section>
      </main>

      <BottomNav />
    </div>
  );
}
