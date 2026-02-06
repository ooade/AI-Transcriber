import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'


// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react()
  ],
  server: {
    host: true, // Needed for Docker container port mapping to work
    port: 5173,
    watch: {
      usePolling: true // Needed for hot reload in some Docker environments (e.g. Windows/some Linux)
    }
  }
})
