import { useEffect, useRef, useState } from "react";

type UseResizableDetailPanelOptions = {
  initialWidth?: number;
  minWidth?: number;
  maxWidthPadding?: number;
  narrowViewportBreakpoint?: number;
};

const DEFAULT_OPTIONS: Required<UseResizableDetailPanelOptions> = {
  initialWidth: 420,
  minWidth: 320,
  maxWidthPadding: 420,
  narrowViewportBreakpoint: 1024,
};

export function useResizableDetailPanel<T>(options?: UseResizableDetailPanelOptions) {
  const merged = { ...DEFAULT_OPTIONS, ...options };
  const [selectedDetail, setSelectedDetail] = useState<T | null>(null);
  const [panelWidth, setPanelWidth] = useState(merged.initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);
  const previousBodyUserSelectRef = useRef<string>("");
  const previousBodyCursorRef = useRef<string>("");

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);

    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!isResizing) {
      return;
    }

    const handleMove = (event: PointerEvent) => {
      const widthFromRight = window.innerWidth - event.clientX;
      const maxWidth = Math.min(760, window.innerWidth - merged.maxWidthPadding);
      const clampedWidth = Math.min(
        Math.max(widthFromRight, merged.minWidth),
        Math.max(merged.minWidth, maxWidth),
      );
      setPanelWidth(clampedWidth);
    };

    const handleUp = () => {
      setIsResizing(false);
    };

    const handleWindowBlur = () => {
      setIsResizing(false);
    };

    previousBodyUserSelectRef.current = document.body.style.userSelect;
    previousBodyCursorRef.current = document.body.style.cursor;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      document.body.style.userSelect = previousBodyUserSelectRef.current;
      document.body.style.cursor = previousBodyCursorRef.current;
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
      window.removeEventListener("blur", handleWindowBlur);
    };
  }, [isResizing, merged.maxWidthPadding, merged.minWidth]);

  return {
    selectedDetail,
    setSelectedDetail,
    panelWidth,
    isResizing,
    startResizing: () => setIsResizing(true),
    isNarrowViewport: viewportWidth < merged.narrowViewportBreakpoint,
    closeDetail: () => setSelectedDetail(null),
  };
}
