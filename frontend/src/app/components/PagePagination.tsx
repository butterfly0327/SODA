import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";

type PagePaginationProps = {
	currentPage: number;
	totalPages: number;
	totalItems?: number;
	alwaysShow?: boolean;
	variant?: "default" | "community";
	onPageChange: (page: number) => void;
};

export function PagePagination({
	currentPage,
	totalPages,
	totalItems = 0,
	alwaysShow = false,
	variant = "default",
	onPageChange,
}: PagePaginationProps) {
	if (totalItems <= 0) {
		return null;
	}

	if (!alwaysShow && totalPages < 1) {
		return null;
	}

	const pageStart = Math.max(0, currentPage - 2);
	const pageEnd = Math.min(totalPages, pageStart + 5);
	const pageNumbers = Array.from(
		{ length: Math.max(0, pageEnd - pageStart) },
		(_, index) => pageStart + index,
	);
	const isCommunityVariant = variant === "community";

	return (
		<div className="mt-8 flex flex-wrap items-center justify-center gap-1">
			<Button
				variant="outline"
				disabled={currentPage === 0}
				onClick={() => onPageChange(0)}
				className={
					isCommunityVariant
						? `h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white disabled:cursor-not-allowed ${
								currentPage === 0
									? "text-muted-foreground/50 hover:text-muted-foreground/50"
									: "text-muted-foreground hover:text-muted-foreground"
							}`
						: "h-8 w-8 rounded-none border-border p-0 text-muted-foreground/50 cursor-pointer disabled:cursor-not-allowed"
				}
			>
				<ChevronsLeft className="w-3.5 h-3.5" />
			</Button>
			<Button
				variant="outline"
				disabled={currentPage === 0}
				onClick={() => onPageChange(Math.max(0, currentPage - 1))}
				className={
					isCommunityVariant
						? `h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white disabled:cursor-not-allowed ${
								currentPage === 0
									? "text-muted-foreground/50 hover:text-muted-foreground/50"
									: "text-muted-foreground hover:text-muted-foreground"
							}`
						: "h-8 w-8 rounded-none border-border p-0 text-muted-foreground/50 cursor-pointer disabled:cursor-not-allowed"
				}
			>
				<ChevronLeft className="w-3.5 h-3.5" />
			</Button>
			{pageNumbers.map((pageNumber) => (
				<Button
					key={pageNumber}
					onClick={() => onPageChange(pageNumber)}
					variant={pageNumber === currentPage ? "default" : "outline"}
					className={
						pageNumber === currentPage
							? isCommunityVariant
								? "inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-[#4f76df] bg-[#4f76df] p-0 text-xs leading-none text-white hover:bg-[#4f76df]"
								: "inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-none border border-[#4f76df] bg-[#4f76df] p-0 text-xs leading-none text-white hover:bg-[#4f76df]"
							: isCommunityVariant
								? "inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-border bg-white p-0 text-xs leading-none text-foreground hover:bg-white hover:text-foreground"
								: "inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-none border border-border bg-white p-0 text-xs leading-none text-foreground hover:bg-white"
					}
				>
					<span className="inline-block w-[1ch] text-center tabular-nums">{pageNumber + 1}</span>
				</Button>
			))}
			<Button
				variant="outline"
				disabled={currentPage >= totalPages - 1}
				onClick={() => onPageChange(Math.min(totalPages - 1, currentPage + 1))}
				className={
					isCommunityVariant
						? `h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white disabled:cursor-not-allowed ${
								currentPage >= totalPages - 1
									? "text-muted-foreground/50 hover:text-muted-foreground/50"
									: "text-muted-foreground hover:text-muted-foreground"
							}`
						: "h-8 w-8 rounded-none border-border p-0 text-muted-foreground/50 cursor-pointer disabled:cursor-not-allowed"
				}
			>
				<ChevronRight className="w-3.5 h-3.5" />
			</Button>
			<Button
				variant="outline"
				disabled={currentPage >= totalPages - 1}
				onClick={() => onPageChange(Math.max(0, totalPages - 1))}
				className={
					isCommunityVariant
						? `h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white disabled:cursor-not-allowed ${
								currentPage >= totalPages - 1
									? "text-muted-foreground/50 hover:text-muted-foreground/50"
									: "text-muted-foreground hover:text-muted-foreground"
							}`
						: "h-8 w-8 rounded-none border-border p-0 text-muted-foreground/50 cursor-pointer disabled:cursor-not-allowed"
				}
			>
				<ChevronsRight className="w-3.5 h-3.5" />
			</Button>
		</div>
	);
}
