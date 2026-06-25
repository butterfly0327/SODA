import { ReactNode } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface LayoutProps {
  children: ReactNode;
  showHeader?: boolean;
}

export function Layout({ children, showHeader = false }: LayoutProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* 네비게이션 바 */}
      <Navbar />
      
      <div className="flex flex-1 overflow-hidden pt-13">
        {/* 사이드바 */}
        <Sidebar />

        {/* 메인 콘텐츠 영역 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {showHeader && (
            <div className="shrink-0 bg-background">
              <Header />
            </div>
          )}
          <div className="flex-1 flex flex-col overflow-hidden">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
