import fs from 'fs'
import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const repoRoot = path.resolve(__dirname, '..');
  const repoModeEnvFile = path.resolve(repoRoot, `.env.${mode}`);
  const repoModeLocalEnvFile = path.resolve(repoRoot, `.env.${mode}.local`);
  const envDir =
    fs.existsSync(repoModeEnvFile) || fs.existsSync(repoModeLocalEnvFile)
      ? repoRoot
      : process.cwd();
  const env = loadEnv(mode, envDir, '');
  const publicBasePath = env.VITE_PUBLIC_BASE_PATH?.trim() || '/';
  const allowedHosts =
    env.VITE_ALLOWED_HOSTS?.split(',')
      .map((host) => host.trim())
      .filter(Boolean) ?? ['localhost', '127.0.0.1', 'j14e105.p.ssafy.io'];
  const backendOrigin =
    env.VITE_BACKEND_ORIGIN ||
    (mode === 'dev'
      ? 'https://j14e105.p.ssafy.io/dev'
      : 'http://localhost:8080');

  return {
    base: publicBasePath,
    envDir,
    envPrefix: ['VITE_', 'SSAFY_'],
    plugins: [
      // The React and Tailwind plugins are both required for Make, even if
      // Tailwind is not being actively used – do not remove them
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        // Alias @ to the src directory
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      allowedHosts,
      proxy: {
        '/api': {
          target: backendOrigin,
          changeOrigin: true,
        },
        '/v1': {
          target: backendOrigin,
          changeOrigin: true,
        },
        '/oauth': {
          target: backendOrigin,
          changeOrigin: true,
        },
      },
    },

    // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
    assetsInclude: ['**/*.svg', '**/*.csv'],
  };
})
