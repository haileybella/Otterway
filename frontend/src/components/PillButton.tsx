import type { ReactNode } from 'react';
import './PillButton.css';

type Props = {
  children: ReactNode;
  icon?: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'soft';
  height?: number;
  onClick?: () => void;
  ariaLabel?: string;
};

export function PillButton({ children, icon, variant = 'primary', height = 50, onClick, ariaLabel }: Props) {
  return (
    <button
      className={`pill-button pill-button--${variant}`}
      style={{ height }}
      onClick={onClick}
      aria-label={ariaLabel}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
