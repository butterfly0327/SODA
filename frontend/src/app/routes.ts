import { createElement } from "react";
import { createBrowserRouter } from "react-router";
import { ProtectedRoute } from "./components/ProtectedRoute";

const rawBasePath = import.meta.env.BASE_URL || "/";
const routerBasePath =
  rawBasePath === "/" ? "/" : rawBasePath.replace(/\/$/, "");

function protectedRoute<ComponentProps extends object>(
  Component: (props: ComponentProps) => JSX.Element
) {
  return function ProtectedPage(props: ComponentProps) {
    return createElement(ProtectedRoute, null, createElement(Component, props));
  };
}

export const router = createBrowserRouter([
	{
		path: "/",
		lazy: async () => {
			const { HomePage } = await import("./pages/HomePage");
			return { Component: HomePage };
		},
	},
	{
		path: "/signup",
		lazy: async () => {
			const { SignupPage } = await import("./pages/SignupPage");
			return { Component: SignupPage };
		},
	},
	{
		path: "/auth/callback",
		lazy: async () => {
			const { AuthCallbackPage } = await import("./pages/AuthCallbackPage");
			return { Component: AuthCallbackPage };
		},
	},
	{
		path: "/search",
		lazy: async () => {
			const { SearchPage } = await import("./pages/SearchPage");
			return { Component: protectedRoute(SearchPage) };
		},
	},
	{
		path: "/bookmark",
		lazy: async () => {
			const { BookmarkPage } = await import("./pages/BookmarkPage");
			return { Component: protectedRoute(BookmarkPage) };
		},
	},
	{
		path: "/resource/:id",
		lazy: async () => {
			const { ResourceDetailPage } = await import("./pages/ResourceDetailPage");
			return { Component: protectedRoute(ResourceDetailPage) };
		},
	},
	{
		path: "/community",
		lazy: async () => {
			const { CommunityPage } = await import("./pages/CommunityPage");
			return { Component: protectedRoute(CommunityPage) };
		},
	},
	{
		path: "/community/:id",
		lazy: async () => {
			const { CommunityDetailPage } = await import("./pages/CommunityDetailPage");
			return { Component: protectedRoute(CommunityDetailPage) };
		},
	},
	{
		path: "/community/new",
		lazy: async () => {
			const { CommunityWritePage } = await import("./pages/CommunityWritePage");
			return { Component: protectedRoute(CommunityWritePage) };
		},
	},
	{
		path: "/community/:id/edit",
		lazy: async () => {
			const { CommunityWritePage } = await import("./pages/CommunityWritePage");
			return { Component: protectedRoute(CommunityWritePage) };
		},
	},
	{
		path: "/mypage",
		lazy: async () => {
			const { MyPage } = await import("./pages/MyPage");
			return { Component: protectedRoute(MyPage) };
		},
	},
	{
		path: "/mypage/activity",
		lazy: async () => {
			const { MyActivityPage } = await import("./pages/MyActivityPage");
			return { Component: protectedRoute(MyActivityPage) };
		},
	},
	{
		path: "/settings",
		lazy: async () => {
			const { SettingsPage } = await import("./pages/SettingsPage");
			return { Component: protectedRoute(SettingsPage) };
		},
	},
	{
		path: "*",
		lazy: async () => {
			const { NotFoundPage } = await import("./pages/NotFoundPage");
			return { Component: protectedRoute(NotFoundPage) };
		},
	},
], {
	basename: routerBasePath,
});
