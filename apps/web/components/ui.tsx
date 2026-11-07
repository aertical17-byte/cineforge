"use client";

import {ButtonHTMLAttributes, DetailedHTMLProps, forwardRef, InputHTMLAttributes, ReactNode} from "react";

type ButtonProps = DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
};

export function Button({className = "", variant = "primary", size = "md", ...rest}: ButtonProps) {
  const base = "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.99]";
  const sizes = {sm: "text-xs px-3 py-1.5", md: "text-sm px-4 py-2.5", lg: "text-[15px] px-5 py-3"}[size];
  const variants = {
    primary: "bg-byz-500 hover:bg-byz-400 text-white shadow-glow",
    ghost: "text-ink-100 hover:bg-ink-700",
    outline: "border border-ink-600 hover:border-byz-400 text-ink-100 bg-ink-850 hover:bg-ink-800",
    danger: "bg-ember hover:bg-ember-600 text-white"
  }[variant];
  return <button className={`${base} ${sizes} ${variants} ${className}`} {...rest} />;
}

export function Input({className = "", ...rest}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-xl border border-ink-600 bg-ink-900 px-3 py-2.5 text-sm text-ink-100 placeholder-ink-300 outline-none focus:border-byz-400 focus:ring-2 focus:ring-byz-500/20 ${className}`}
      {...rest}
    />
  );
}

export function Card({children, className = ""}: {children: ReactNode; className?: string}) {
  return <div className={`rounded-xl2 border border-ink-700 bg-ink-850 shadow-card ${className}`}>{children}</div>;
}

export function Badge({children, tone = "neutral", className = ""}: {children: ReactNode; tone?: "neutral" | "accent" | "warn" | "err" | "ok"; className?: string}) {
  const tones = {
    neutral: "bg-ink-700 text-ink-100",
    accent: "bg-byz-500/15 text-byz-300 border border-byz-500/25",
    warn: "bg-amber-500/15 text-amber-300",
    err: "bg-ember/15 text-ember",
    ok: "bg-emerald-500/15 text-emerald-300",
  }[tone];
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${tones} ${className}`}>{children}</span>;
}

export function Modal({open, onClose, title, children}: {open: boolean; onClose: () => void; title?: string; children: ReactNode}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="modal">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-xl2 border border-ink-600 bg-ink-850 p-5 shadow-card">
        {title && <h3 className="mb-3 text-lg font-semibold">{title}</h3>}
        {children}
      </div>
    </div>
  );
}

export function EmptyState({title, body, action}: {title: string; body: string; action?: ReactNode}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl2 border border-dashed border-ink-600 bg-ink-900/50 px-8 py-16 text-center">
      <div className="text-xl">✦</div>
      <h3 className="font-semibold text-ink-100">{title}</h3>
      <p className="max-w-sm text-sm text-ink-300">{body}</p>
      {action}
    </div>
  );
}

export function Skeleton({className = ""}: {className?: string}) {
  return <div className={`animate-pulse rounded-xl bg-ink-700/60 ${className}`} />;
}

export function Tabs({items, active, onChange}: {items: {id: string; label: string}[]; active: string; onChange: (id: string) => void}) {
  return (
    <div role="tablist" className="flex gap-1 rounded-xl border border-ink-700 bg-ink-900 p-1">
      {items.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={active === t.id}
          onClick={() => onChange(t.id)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${active === t.id ? "bg-byz-500/20 text-byz-200" : "text-ink-300 hover:text-ink-100"}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export const Field = ({label, children, hint}: {label: string; children: ReactNode; hint?: string}) => (
  <label className="block">
    <div className="mb-1.5 flex items-baseline justify-between">
      <span className="text-xs font-medium text-ink-200">{label}</span>
      {hint && <span className="text-[11px] text-ink-300">{hint}</span>}
    </div>
    {children}
  </label>
);
