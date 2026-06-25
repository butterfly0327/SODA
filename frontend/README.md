
  # 웹사이트 구조 설계

  This is a code bundle for 웹사이트 구조 설계. The original project is available at https://www.figma.com/design/RWlPLGFFZWV2eZ9bVzbVgv/%EC%9B%B9%EC%82%AC%EC%9D%B4%ED%8A%B8-%EA%B5%AC%EC%A1%B0-%EC%84%A4%EA%B3%84.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the local frontend against the remote dev API at `https://j14e105.p.ssafy.io/dev`.

  Frontend local development now reads repo root env files:

  - `.env.dev`
  - `.env.dev.local`
  - `.env.prod`
  - `.env.prod.local`

  Recommended base keys for `.env.dev`:

  - `VITE_BACKEND_ORIGIN=https://j14e105.p.ssafy.io/dev`
  - `VITE_API_URL=/api/v1`
  - `VITE_PUBLIC_BASE_PATH=/`
  - `VITE_ALLOWED_HOSTS=localhost,127.0.0.1,j14e105.p.ssafy.io`
  - `SSAFY_AUTHORIZE_URL=https://project.ssafy.com/oauth/sso-check`
  - `SSAFY_CLIENT_ID=...`
  - `SSAFY_REDIRECT_URL=https://j14e105.p.ssafy.io/dev/auth/callback`

  Local-only overrides should go in `.env.dev.local`:

  - `SSAFY_REDIRECT_URL=http://localhost:5173/auth/callback`
  
