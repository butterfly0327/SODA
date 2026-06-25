import { useEffect } from "react";
import { buildSsafyAuthorizeUrl } from "../lib/ssafyOAuth";

export function SsoRedirectPage() {
  useEffect(() => {
    window.location.href = buildSsafyAuthorizeUrl();
  }, []);

  return (
    <div className="min-h-screen bg-white px-4 py-8 sm:px-6">
      <div className="mx-auto flex min-h-screen w-full max-w-[460px] flex-col items-center justify-center">
        <p className="text-sm text-[#374151]">SSAFY 로그인 페이지로 이동 중입니다...</p>
      </div>
    </div>
  );
}
