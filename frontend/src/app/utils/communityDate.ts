const ABSOLUTE_DATE_TIME_WITH_OPTIONAL_SECONDS =
	/^\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}(?::\d{2})?$/;

function formatToMinuteLabel(targetDate: Date) {
	const year = targetDate.getFullYear();
	const month = String(targetDate.getMonth() + 1).padStart(2, "0");
	const day = String(targetDate.getDate()).padStart(2, "0");
	const hour = String(targetDate.getHours()).padStart(2, "0");
	const minute = String(targetDate.getMinutes()).padStart(2, "0");

	return `${year}.${month}.${day} ${hour}:${minute}`;
}

export function getHoursAgoFromCreatedAt(createdAt: string) {
	if (createdAt.includes("방금 전")) {
		return 0;
	}
	if (createdAt.includes("분 전")) {
		return Number(createdAt.replace("분 전", "").trim()) / 60;
	}
	if (createdAt.includes("시간 전")) {
		return Number(createdAt.replace("시간 전", "").trim());
	}
	if (createdAt.includes("일 전")) {
		return Number(createdAt.replace("일 전", "").trim()) * 24;
	}

	if (ABSOLUTE_DATE_TIME_WITH_OPTIONAL_SECONDS.test(createdAt)) {
		const [datePart, timePart] = createdAt.split(" ");
		const [year, month, day] = datePart.split(".").map(Number);
		const [hour, minute] = timePart.split(":").map(Number);
		const parsedDate = new Date(year, month - 1, day, hour, minute);
		if (!Number.isNaN(parsedDate.getTime())) {
			return Math.max(
				0,
				(Date.now() - parsedDate.getTime()) / (1000 * 60 * 60),
			);
		}
	}

	const parsedDate = new Date(createdAt);
	if (!Number.isNaN(parsedDate.getTime())) {
		return Math.max(0, (Date.now() - parsedDate.getTime()) / (1000 * 60 * 60));
	}

	return Number.MAX_SAFE_INTEGER;
}

export function formatCreatedAt(createdAt: string) {
	if (ABSOLUTE_DATE_TIME_WITH_OPTIONAL_SECONDS.test(createdAt)) {
		return createdAt.slice(0, 16);
	}

	let minutesAgo: number | null = null;
	if (createdAt.includes("방금 전")) {
		minutesAgo = 0;
	} else if (createdAt.includes("분 전")) {
		minutesAgo = Number(createdAt.replace("분 전", "").trim());
	} else if (createdAt.includes("시간 전")) {
		minutesAgo = Number(createdAt.replace("시간 전", "").trim()) * 60;
	} else if (createdAt.includes("일 전")) {
		minutesAgo = Number(createdAt.replace("일 전", "").trim()) * 24 * 60;
	}

	if (minutesAgo === null || Number.isNaN(minutesAgo)) {
		const parsedDate = new Date(createdAt);
		if (!Number.isNaN(parsedDate.getTime())) {
			return formatToMinuteLabel(parsedDate);
		}
		return createdAt;
	}

	const targetDate = new Date(Date.now() - minutesAgo * 60 * 1000);
	return formatToMinuteLabel(targetDate);
}
