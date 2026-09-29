'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useFocusTrap } from '@/lib/hooks/useFocusTrap';
import { useIsMobileModal } from '@/lib/hooks/useMediaQuery';

interface ResponsiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  maxWidth?: 'sm' | 'md' | 'lg' | '3xl';
  title?: string;
  children: React.ReactNode;
  zIndex?: number;
}

const MAX_WIDTH_CLASSES: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  '3xl': 'max-w-3xl',
};

export function ResponsiveModal({
  isOpen,
  onClose,
  maxWidth = 'md',
  title,
  children,
  zIndex = 50,
}: ResponsiveModalProps) {
  const focusTrapRef = useFocusTrap<HTMLDivElement>();
  const isMobile = useIsMobileModal();
  const [sheetVisible, setSheetVisible] = useState(false);
  const [dragDeltaY, setDragDeltaY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const startYRef = useRef(0);
  const sheetRef = useRef<HTMLDivElement>(null);

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return;
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Mobile sheet entrance animation
  useEffect(() => {
    if (isOpen && isMobile) {
      // Delay to allow the component to mount before animating in
      const timer = requestAnimationFrame(() => {
        setSheetVisible(true);
      });
      return () => cancelAnimationFrame(timer);
    } else {
      setSheetVisible(false);
    }
  }, [isOpen, isMobile]);

  const handleBackdrop = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  // Touch gesture handlers for drag handle
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startYRef.current = e.touches[0].clientY;
    setIsDragging(true);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging) return;
    const currentY = e.touches[0].clientY;
    const delta = currentY - startYRef.current;
    // Only allow dragging down (positive delta)
    if (delta > 0) {
      setDragDeltaY(delta);
    }
  }, [isDragging]);

  const handleTouchEnd = useCallback(() => {
    if (dragDeltaY > 100) {
      onClose();
    }
    setDragDeltaY(0);
    setIsDragging(false);
  }, [dragDeltaY, onClose]);

  if (!isOpen) return null;

  // Desktop: centered modal
  if (!isMobile) {
    return (
      <div
        className={`fixed inset-0 z-${zIndex} flex items-center justify-center bg-black/60`}
        style={{ zIndex }}
        onClick={handleBackdrop}
      >
        <div
          ref={focusTrapRef}
          className={`card w-full ${MAX_WIDTH_CLASSES[maxWidth]} mx-4 max-h-[90vh] overflow-y-auto`}
          role="dialog"
          aria-modal="true"
        >
          {title && <h2 className="section-title text-base mb-4">{title}</h2>}
          {children}
        </div>
      </div>
    );
  }

  // Mobile: bottom sheet
  return (
    <div
      className="fixed inset-0 bg-black/60"
      style={{ zIndex }}
      onClick={handleBackdrop}
    >
      <div
        ref={(el) => {
          // Assign to both refs
          (sheetRef as React.MutableRefObject<HTMLDivElement | null>).current = el;
          (focusTrapRef as React.MutableRefObject<HTMLDivElement | null>).current = el;
        }}
        className={`fixed bottom-0 left-0 right-0 bg-[#0c0e42] border border-secondary-muted/30 border-b-0 rounded-t-2xl transition-transform duration-300 ease-out`}
        style={{
          zIndex: zIndex + 1,
          transform: sheetVisible
            ? `translateY(${dragDeltaY}px)`
            : 'translateY(100%)',
          transition: isDragging ? 'none' : undefined,
        }}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag handle */}
        <div
          className="py-3 cursor-grab active:cursor-grabbing"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="w-10 h-1 bg-white/30 rounded-full mx-auto" />
        </div>

        {/* Title */}
        {title && (
          <div className="px-4">
            <h2 className="section-title text-base mb-4">{title}</h2>
          </div>
        )}

        {/* Content area */}
        <div className="px-4 max-h-[85vh] overflow-y-auto safe-bottom pb-6">
          {children}
        </div>
      </div>
    </div>
  );
}
