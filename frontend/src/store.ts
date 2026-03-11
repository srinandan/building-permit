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

import { create } from 'zustand';

interface User {
  id: number;
  email: string;
  name: string;
}

interface Property {
  id: number;
  user_id: number;
  address: string;
  city: string;
  zip_code: string;
}

interface AuthState {
  user: User | null;
  currentProperty: Property | null;
  login: (user: User) => void;
  logout: () => void;
  setCurrentProperty: (property: Property | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  currentProperty: null,
  login: (user) => set({ user }),
  logout: () => set({ user: null, currentProperty: null }),
  setCurrentProperty: (property) => set({ currentProperty: property }),
}));
