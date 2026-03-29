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

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';

const API_URL = '';

export function NewPermit() {
  const { user, currentProperty, setCurrentProperty } = useAuthStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [availableAddresses, setAvailableAddresses] = useState<string[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<string>(currentProperty?.address || '');
  const [mapCenter, setMapCenter] = useState<{lat: number, lng: number} | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
  });

  const [formData, setFormData] = useState({
    projectName: '',
    permitType: 'Residential',
    streetAddress: currentProperty?.address || '',
    city: currentProperty?.city || '',
    zipCode: currentProperty?.zip_code || '',
    description: ''
  });

  const handleAddressSelect = useCallback(async (address: string) => {
    setSelectedAddress(address);
    setFormData(prev => ({ ...prev, streetAddress: address }));
    setMapError(null);
    setMapCenter(null);

    try {
      // First ensure the property exists in the Go DB for this user
      if (user?.id) {
        try {
          const createPropRes = await axios.post(`${API_URL}/api/users/${user.id}/properties`, {
            address: address,
            city: '', // Extract from address if possible, but leaving blank for now
            zip_code: ''
          });
          setCurrentProperty(createPropRes.data);
        } catch (propErr) {
          console.error("Non-fatal: Failed to register property in backend DB", propErr);
        }
      }

      // Fetch map data using the new API endpoint
      const mapRes = await axios.post(`${API_URL}/api/map/search`, { address });

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
    }
  }, [user, setCurrentProperty]);

  useEffect(() => {
    if (user?.email) {
      axios.get(`${API_URL}/api/users/email/${user.email}/properties`)
        .then(res => {
          if (res.data && res.data.properties) {
            setAvailableAddresses(res.data.properties);
            if (!selectedAddress && res.data.properties.length > 0) {
              handleAddressSelect(res.data.properties[0]);
            } else if (selectedAddress && !mapCenter && !mapError) {
              // If selectedAddress is already set (e.g. from currentProperty)
              // make sure we load the map data for it on mount
              handleAddressSelect(selectedAddress);
            }
          }
        })
        .catch(err => console.error("Failed to load properties:", err));
    }
  }, [user, handleAddressSelect, selectedAddress, mapCenter, mapError]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleTypeSelect = (type: string) => {
    setFormData(prev => ({ ...prev, permitType: type }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentProperty) {
        setError("No property selected or available.");
        return;
    }

    if (!formData.projectName.trim()) {
        setError("Project Name is required.");
        return;
    }

    setLoading(true);
    setError(null);

    try {
        const response = await axios.post(`${API_URL}/api/properties/${currentProperty.id}/permits`, {
            title: formData.projectName,
            description: formData.description || `Permit application for ${formData.projectName}`
        });

        // Navigate to the new permit details page
        navigate(`/permit/${response.data.id}`);
    } catch(err: any) {
        console.error("Failed to create permit", err);
        setError(err.response?.data?.error || 'Failed to create permit application. Please try again.');
        setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="bg-surface-bright text-on-surface font-body min-h-screen flex flex-col pb-20">
      {/* Top Navigation */}
      <header className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between px-6 h-16 w-full">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="text-slate-500 hover:bg-slate-50 transition-colors active:scale-95 duration-200"
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <h1 className="font-['Inter'] font-bold tracking-tight text-slate-900 text-lg">New Application</h1>
          </div>
          <div className="flex items-center gap-2">
            <h1 className="text-xs sm:text-sm md:text-base leading-tight text-right font-black text-blue-800 tracking-tight">San Paloma County Permit Hub</h1>
            <img src="/spc_logo.png" alt="San Paloma County Permit Hub Logo" className="h-6 w-6 object-contain rounded-full bg-white shadow-sm" />
          </div>
        </div>
      </header>

      <main className="mt-16 flex-grow container max-w-lg mx-auto px-6 py-8">
        {/* Progress Stepper (Mobile Layout) */}
        <section className="mb-10">
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-end">
              <span className="text-xs font-bold tracking-widest text-primary uppercase">Step 1 of 4</span>
              <span className="text-sm font-semibold text-on-surface-variant">Project Details</span>
            </div>
            <div className="h-2 w-full bg-primary-fixed rounded-full overflow-hidden">
              <div className="h-full bg-primary w-1/4 rounded-full"></div>
            </div>
          </div>
        </section>

        {/* Form Content */}
        <section className="space-y-10">
          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold tracking-tight text-on-surface">Submission Details</h2>
            <p className="text-on-surface-variant text-sm leading-relaxed">Provide the foundational information for your building permit application. This will help us route your request to the correct department.</p>
          </div>

          {error && (
              <div className="p-4 bg-error-container text-on-error-container rounded-xl text-sm font-medium">
                  {error}
              </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Group: Identity */}
            <div className="p-6 rounded-2xl bg-surface-container-low space-y-6">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">Project Name</label>
                <div className="relative group">
                  <input
                    name="projectName"
                    value={formData.projectName}
                    onChange={handleInputChange}
                    className="w-full bg-surface-container-lowest border-none rounded-xl py-4 px-4 text-on-surface focus:ring-2 focus:ring-primary placeholder:text-outline/50 transition-all duration-200 shadow-sm outline-none"
                    placeholder="e.g. Smith Residence Deck"
                    type="text"
                    required
                  />
                  <div className="absolute bottom-0 left-0 h-0.5 bg-primary w-0 group-focus-within:w-full transition-all duration-300"></div>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">Permit Type</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleTypeSelect('Residential')}
                    className={`flex flex-col items-center justify-center p-4 rounded-xl active:scale-95 duration-150 ${formData.permitType === 'Residential' ? 'bg-primary text-white shadow-md' : 'bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-colors'}`}
                  >
                    <span className="material-symbols-outlined mb-2" style={formData.permitType === 'Residential' ? { fontVariationSettings: "'FILL' 1" } : {}}>home</span>
                    <span className="text-[11px] font-bold uppercase tracking-wider">Residential</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTypeSelect('Commercial')}
                    className={`flex flex-col items-center justify-center p-4 rounded-xl active:scale-95 duration-150 ${formData.permitType === 'Commercial' ? 'bg-primary text-white shadow-md' : 'bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-colors'}`}
                  >
                    <span className="material-symbols-outlined mb-2" style={formData.permitType === 'Commercial' ? { fontVariationSettings: "'FILL' 1" } : {}}>business</span>
                    <span className="text-[11px] font-bold uppercase tracking-wider">Commercial</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Group: Location */}
            <div className="p-6 rounded-2xl bg-surface-container-low space-y-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-primary text-sm">location_on</span>
                <h3 className="text-[11px] font-black uppercase tracking-widest text-on-surface">Project Site</h3>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">Select Property</label>
                <select
                  name="streetAddress"
                  value={selectedAddress}
                  onChange={(e) => handleAddressSelect(e.target.value)}
                  className="w-full bg-surface-container-lowest border-none rounded-xl py-4 px-4 text-on-surface focus:ring-2 focus:ring-primary shadow-sm outline-none cursor-pointer"
                  required
                >
                  <option value="" disabled>Select an address associated with your account...</option>
                  {availableAddresses.map((addr) => (
                    <option key={addr} value={addr}>{addr}</option>
                  ))}
                </select>
                {availableAddresses.length === 0 && (
                   <p className="text-xs text-error mt-2 ml-1">No properties found for your account.</p>
                )}
              </div>

              {/* Map Rendering Area */}
              {selectedAddress && (
                 <div className="mt-4 rounded-xl overflow-hidden shadow-inner bg-surface-container-lowest min-h-[250px] relative border border-outline-variant/30">
                    {mapError ? (
                        <div className="absolute inset-0 flex items-center justify-center bg-surface-container">
                            <img
                                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25'%3E%3Crect width='100%25' height='100%25' fill='%23f1f5f9'/%3E%3Ctext x='50%25' y='50%25' font-family='sans-serif' font-size='14' fill='%2394a3b8' text-anchor='middle' dominant-baseline='middle'%3EMap preview unavailable%3C/text%3E%3C/svg%3E"
                                alt="Map placeholder"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    ) : !isLoaded || (!mapCenter && !mapError) ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-on-surface-variant">
                          <Loader2 className="w-8 h-8 animate-spin mb-2" />
                          <span className="text-sm font-medium">Loading Map...</span>
                        </div>
                    ) : mapCenter ? (
                        <GoogleMap
                          mapContainerStyle={{ width: '100%', height: '250px' }}
                          center={mapCenter}
                          zoom={17}
                          options={{
                            disableDefaultUI: true,
                            zoomControl: true,
                            fullscreenControl: true,
                          }}
                        >
                           <Marker position={mapCenter} />
                        </GoogleMap>
                    ) : null}
                 </div>
              )}
            </div>

            {/* Group: Description */}
            <div className="p-6 rounded-2xl bg-surface-container-low space-y-4">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant ml-1">Project Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                className="w-full bg-surface-container-lowest border-none rounded-xl py-4 px-4 text-on-surface focus:ring-2 focus:ring-primary shadow-sm resize-none outline-none"
                placeholder="Describe the scope of work, including structural changes, plumbing, or electrical modifications..."
                rows={4}
                maxLength={500}
              ></textarea>
              <p className="text-[10px] text-on-surface-variant/70 italic px-1">Maximum 500 characters. Be as specific as possible for faster processing.</p>
            </div>

            {/* Action Button */}
            <div className="pt-4 pb-8">
              <button
                type="submit"
                disabled={loading}
                className={`w-full h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full font-bold tracking-wide flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-all duration-200 ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                {loading ? (
                    <><Loader2 className="w-5 h-5 animate-spin" /> Processing...</>
                ) : (
                    <>
                        Continue to Step 2
                        <span className="material-symbols-outlined">arrow_forward</span>
                    </>
                )}
              </button>
              <p className="text-center mt-4 text-xs text-on-surface-variant font-medium">Your progress is automatically saved as a draft.</p>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}