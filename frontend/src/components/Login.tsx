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

import React, { useState } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store';
import { useNavigate } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/login`, { email });
      login(response.data);
      navigate('/');
    } catch (error) {
      console.error('Login failed', error);
      alert('Login failed. Ensure API is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface font-body flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center flex flex-col items-center px-4">
        <img src="/spc_logo.png" alt="San Paloma County Permit Hub Logo" className="h-24 w-24 object-contain rounded-full bg-white shadow-sm mb-6" />
        <h2 className="text-3xl font-black tracking-tight text-on-surface uppercase font-['Inter']">
          San Paloma County Permit Hub
        </h2>
        <p className="mt-2 text-sm font-semibold tracking-wider uppercase text-tertiary">
          Permit Hub
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-md px-6">
        <div className="bg-surface-container-lowest py-10 px-6 sm:px-10 shadow-lg shadow-slate-200/50 rounded-3xl border border-surface-container-highest">
          <form className="space-y-8" onSubmit={handleLogin}>
            <div>
              <label htmlFor="email" className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">
                Email address
              </label>
              <div className="mt-1 relative group">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-surface-container-low border-none rounded-xl py-4 px-4 text-on-surface focus:ring-2 focus:ring-primary placeholder:text-outline/50 transition-all duration-200 shadow-sm"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 ml-1">
                Password
              </label>
              <div className="mt-1 relative group">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface-container-low border-none rounded-xl py-4 px-4 text-on-surface focus:ring-2 focus:ring-primary placeholder:text-outline/50 transition-all duration-200 shadow-sm"
                  placeholder="••••••••"
                />
              </div>
              <p className="mt-2 ml-1 text-[10px] text-tertiary/80 italic font-medium">For demo purposes, any password will work.</p>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full font-bold tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-primary/20 active:scale-95 transition-all duration-200"
              >
                {loading ? 'Signing in...' : 'Sign in'}
                {!loading && <span className="material-symbols-outlined text-sm">login</span>}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
