import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Websocket proxy -- just for demo 
        "/ws": {
          target: "http://localhost:8000",
          ws: true,
    
    },
  },
  },
});
