// frontend/app/logrocket.tsx
'use client';

import { useEffect } from 'react';
import LogRocket from 'logrocket';

export default function LogRocketInit() {
  useEffect(() => {
    try {
      console.log('Initializing LogRocket...');
      LogRocket.init('8akivt/wucupid');
      console.log('LogRocket initialized successfully');
    } catch (error) {
      console.error('Failed to initialize LogRocket:', error);
    }
  }, []);

  return null;
}
