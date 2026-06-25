import { ChevronDown, LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";
import { useClickOutside } from "../../hooks/useClickOutside";
import { userApi } from "../../api/userApi";
import { BrandLogo } from "./BrandLogo";
import { beginSsafyLoginFlow, suppressSsafyAutoLoginOnce } from "../lib/ssafyLoginFlow";

export function Navbar() {
	const navigate = useNavigate();
	const location = useLocation();
	const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
	const userName = useAuthStore((state) => state.user?.name);
	const logout = useAuthStore((state) => state.logout);
	const setCurrentConversation = useChatStore((state) => state.setCurrentConversation);
	const setCurrentProject = useChatStore((state) => state.setCurrentProject);
	const [isDropdownOpen, setIsDropdownOpen] = useState(false);
	const [profileName, setProfileName] = useState<string | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const sanitizeName = (name: string | null | undefined) => {
		const normalizedName = name?.trim();
		if (!normalizedName || normalizedName === "SSAFY 사용자") {
			return "";
		}
		return normalizedName;
	};
	const displayName = sanitizeName(profileName) || sanitizeName(userName);

	const handleGoHome = () => {
		setCurrentProject(null);
		navigate("/", { state: { resetHome: true } });
	};

	const handleLogout = async () => {
		suppressSsafyAutoLoginOnce();
		await logout();
		navigate("/", { replace: true });
		setIsDropdownOpen(false);
	};

	useClickOutside({
		ref: dropdownRef,
		enabled: isDropdownOpen,
		onOutsideClick: () => setIsDropdownOpen(false),
		onEscape: () => setIsDropdownOpen(false),
	});

	useEffect(() => {
		if (!isAuthenticated) {
			setProfileName(null);
			return;
		}

		let isMounted = true;

		void userApi
			.getMyProfile()
			.then((profile) => {
				if (!isMounted) {
					return;
				}
				setProfileName(profile.name ?? null);
			})
			.catch(() => {
				if (!isMounted) {
					return;
				}
				setProfileName(null);
			});

		return () => {
			isMounted = false;
		};
	}, [isAuthenticated]);

	return (
		<nav
			className="fixed top-0 left-0 right-0 w-full bg-white border-b border-border z-50"
			aria-label="메인 네비게이션"
		>
			<div className="w-full pl-14 pr-6 h-13 relative flex items-center justify-between gap-3">
				<div className="absolute left-0 top-1/2 -translate-y-1/2 w-64 flex justify-center">
					<button
						type="button"
						onClick={handleGoHome}
						className="flex items-center cursor-pointer hover:opacity-90 transition-opacity"
						aria-label="홈으로 이동"
					>
						<BrandLogo className="h-10 w-auto object-contain" />
					</button>
				</div>

				{/* 오른쪽: Login/My Page */}
				<div className="ml-auto">
					{isAuthenticated ? (
						<div className="relative" ref={dropdownRef}>
							<button
								type="button"
								onClick={() => setIsDropdownOpen(!isDropdownOpen)}
								aria-haspopup="menu"
								aria-expanded={isDropdownOpen}
								aria-controls="mypage-menu"
							className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm text-foreground cursor-pointer hover:bg-sidebar-accent/50 transition-colors"
						>
								<User className="w-4 h-4" />
								<span className="min-w-[52px]">{displayName}</span>
								<ChevronDown
									className={`w-4 h-4 transition-transform ${isDropdownOpen ? "rotate-180" : ""}`}
								/>
							</button>

							{isDropdownOpen && (
								<div
									id="mypage-menu"
									className="absolute right-0 top-full mt-1 w-40 bg-white border border-border shadow-lg rounded-xl overflow-hidden z-50"
								>
									<div>
										<button
											type="button"
											onClick={() => {
												navigate("/mypage");
												setIsDropdownOpen(false);
											}}
											className="mx-1 my-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left cursor-pointer transition-colors hover:bg-sidebar-accent/50"
										>
											<User className="w-3 h-3" />
										My Page
									</button>
										<button
											type="button"
											onClick={handleLogout}
											className="mx-1 mb-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left cursor-pointer transition-colors hover:bg-sidebar-accent/50"
										>
											<LogOut className="w-3 h-3" />
											Logout
										</button>
									</div>
								</div>
							)}
						</div>
					) : (
						<button
							type="button"
							onClick={() => {
								beginSsafyLoginFlow(
									`${location.pathname}${location.search}${location.hash}`,
								);
							}}
							className="px-4 py-2 rounded-lg font-medium text-sm bg-[#e8f4fd] text-foreground cursor-pointer hover:bg-[#d4eaf7] transition-colors"
						>
							Login
						</button>
					)}
				</div>
			</div>
		</nav>
	);
}
