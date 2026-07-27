'use client'

import * as React from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import * as SwitchPrimitive from '@radix-ui/react-switch'
import * as SliderPrimitive from '@radix-ui/react-slider'
import * as SelectPrimitive from '@radix-ui/react-select'
import * as SeparatorPrimitive from '@radix-ui/react-separator'
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area'
import { cva, type VariantProps } from 'class-variance-authority'
import { Check, ChevronDown, X } from 'lucide-react'

import { cn } from '@/lib/utils'

/* ==========================================================================
   Input
   ========================================================================== */

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode
  suffix?: React.ReactNode
  invalid?: boolean
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, icon, suffix, invalid, ...props }, ref) => (
    <div className="relative flex items-center">
      {icon ? (
        <span className="pointer-events-none absolute left-2.5 text-ink-4 [&_svg]:size-3.5">
          {icon}
        </span>
      ) : null}
      <input
        ref={ref}
        className={cn(
          'h-9 w-full rounded bg-sunken px-3 text-sm text-ink',
          'border border-line/8 shadow-sm',
          'placeholder:text-ink-4',
          'transition-[border-color,box-shadow,background-color] duration-fast',
          'hover:border-line/14',
          'focus:border-gold/40 focus:outline-none focus:ring-2 focus:ring-gold/20',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          icon && 'pl-8',
          suffix && 'pr-9',
          invalid && 'border-danger/50 focus:border-danger/60 focus:ring-danger/20',
          className,
        )}
        {...props}
      />
      {suffix ? (
        <span className="absolute right-2.5 text-ink-4 text-xs">{suffix}</span>
      ) : null}
    </div>
  ),
)
Input.displayName = 'Input'

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'w-full resize-none rounded bg-sunken px-3 py-2 text-sm text-ink',
      'border border-line/8 shadow-sm leading-relaxed',
      'placeholder:text-ink-4',
      'transition-[border-color,box-shadow] duration-fast',
      'hover:border-line/14',
      'focus:border-gold/40 focus:outline-none focus:ring-2 focus:ring-gold/20',
      className,
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'

/** A label plus its control, with optional hint. Used all over settings. */
export function Field({
  label,
  hint,
  htmlFor,
  children,
  className,
  inline,
}: {
  label: string
  hint?: string
  htmlFor?: string
  children: React.ReactNode
  className?: string
  inline?: boolean
}) {
  return (
    <div
      className={cn(
        inline
          ? 'flex items-center justify-between gap-6 py-2.5'
          : 'flex flex-col gap-1.5',
        className,
      )}
    >
      <div className={cn(inline && 'min-w-0 flex-1')}>
        <label
          htmlFor={htmlFor}
          className="block text-sm font-medium text-ink-2"
        >
          {label}
        </label>
        {hint ? (
          <p className="mt-0.5 text-xs leading-relaxed text-ink-4">{hint}</p>
        ) : null}
      </div>
      <div className={cn(inline && 'shrink-0')}>{children}</div>
    </div>
  )
}

/* ==========================================================================
   Badge
   ========================================================================== */

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-sm border px-1.5 py-px ' +
    'text-2xs font-medium whitespace-nowrap [&_svg]:size-3',
  {
    variants: {
      variant: {
        neutral: 'border-line/10 bg-ink/[0.05] text-ink-3',
        gold: 'border-gold/25 bg-gold/10 text-gold',
        indigo: 'border-indigo/25 bg-indigo/10 text-indigo',
        success: 'border-success/25 bg-success/10 text-success',
        warning: 'border-warning/25 bg-warning/10 text-warning',
        danger: 'border-danger/25 bg-danger/10 text-danger',
        outline: 'border-line/14 bg-transparent text-ink-3',
      },
    },
    defaultVariants: { variant: 'neutral' },
  },
)

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

/** A small filled dot, for status in dense lists. */
export function Dot({ className }: { className?: string }) {
  return (
    <span
      className={cn('inline-block size-1.5 shrink-0 rounded-full', className)}
    />
  )
}

/* ==========================================================================
   Dialog
   ========================================================================== */

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
    size?: 'sm' | 'md' | 'lg' | 'xl'
  }
>(({ className, children, size = 'md', ...props }, ref) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay
      className={cn(
        'fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px]',
        'data-[state=open]:animate-fade-in data-[state=closed]:animate-out',
        'data-[state=closed]:fade-out-0',
      )}
    />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2',
        'w-[calc(100vw-3rem)] max-h-[85vh] overflow-hidden',
        'rounded-xl border border-line/10 bg-overlay shadow-xl',
        'flex flex-col',
        'data-[state=open]:animate-scale-in',
        { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }[
          size
        ],
        className,
      )}
      {...props}
    >
      {children}
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
))
DialogContent.displayName = 'DialogContent'

export function DialogHeader({
  title,
  description,
  className,
}: {
  title: string
  description?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 border-b border-line/8 p-5 pb-4',
        className,
      )}
    >
      <div className="min-w-0">
        <DialogPrimitive.Title className="text-lg font-semibold text-ink">
          {title}
        </DialogPrimitive.Title>
        {description ? (
          <DialogPrimitive.Description className="mt-1 text-sm leading-relaxed text-ink-3">
            {description}
          </DialogPrimitive.Description>
        ) : null}
      </div>
      <DialogPrimitive.Close
        className="rounded-sm p-1 text-ink-4 transition-colors duration-fast
                   hover:bg-ink/[0.06] hover:text-ink focus-visible:outline-none"
        aria-label="Close"
      >
        <X className="size-4" />
      </DialogPrimitive.Close>
    </div>
  )
}

export function DialogBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('min-h-0 flex-1 overflow-y-auto p-5', className)} {...props} />
  )
}

export function DialogFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex items-center justify-end gap-2 border-t border-line/8 p-4',
        className,
      )}
      {...props}
    />
  )
}

/* ==========================================================================
   Tooltip
   ========================================================================== */

export const TooltipProvider = TooltipPrimitive.Provider

export function Tooltip({
  children,
  content,
  side = 'top',
  kbd,
  delay = 400,
}: {
  children: React.ReactNode
  content: React.ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  kbd?: string
  delay?: number
}) {
  if (!content) return <>{children}</>
  return (
    <TooltipPrimitive.Root delayDuration={delay}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn(
            'z-50 flex items-center gap-2 rounded-sm px-2 py-1',
            'glass shadow-lg',
            'text-xs text-ink-2',
            'data-[state=delayed-open]:animate-scale-in',
          )}
        >
          {content}
          {kbd ? (
            <kbd className="rounded-[3px] border border-line/12 bg-ink/[0.05]
                            px-1 font-mono text-2xs text-ink-4">
              {kbd}
            </kbd>
          ) : null}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}

/* ==========================================================================
   Tabs
   ========================================================================== */

export const Tabs = TabsPrimitive.Root

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'inline-flex items-center gap-0.5 rounded-lg bg-sunken p-0.5',
      'border border-line/8',
      className,
    )}
    {...props}
  />
))
TabsList.displayName = 'TabsList'

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center gap-1.5 rounded-[calc(var(--r-lg)-4px)]',
      'px-3 py-1.5 text-sm font-medium text-ink-3',
      'transition-all duration-fast',
      'hover:text-ink-2',
      'data-[state=active]:bg-raised data-[state=active]:text-ink',
      'data-[state=active]:shadow-sm',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/40',
      '[&_svg]:size-3.5',
      className,
    )}
    {...props}
  />
))
TabsTrigger.displayName = 'TabsTrigger'

export const TabsContent = TabsPrimitive.Content

/* ==========================================================================
   Switch, Slider, Select, Separator
   ========================================================================== */

export const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root
    ref={ref}
    className={cn(
      'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center',
      'rounded-full border border-line/10 p-0.5',
      'transition-colors duration-normal',
      'data-[state=checked]:bg-gold data-[state=unchecked]:bg-ink/[0.1]',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/40',
      'disabled:cursor-not-allowed disabled:opacity-40',
      className,
    )}
    {...props}
  >
    <SwitchPrimitive.Thumb
      className={cn(
        'pointer-events-none block size-3.5 rounded-full bg-white shadow-sm',
        'transition-transform duration-normal ease-spring',
        'data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0',
      )}
    />
  </SwitchPrimitive.Root>
))
Switch.displayName = 'Switch'

export const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      'relative flex w-full touch-none select-none items-center',
      className,
    )}
    {...props}
  >
    <SliderPrimitive.Track
      className="relative h-1 w-full grow overflow-hidden rounded-full
                 bg-ink/[0.1]"
    >
      <SliderPrimitive.Range className="absolute h-full bg-gold" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      className="block size-3.5 rounded-full border-2 border-gold bg-canvas
                 shadow-sm transition-transform duration-fast
                 hover:scale-110 active:scale-95
                 focus-visible:outline-none focus-visible:ring-2
                 focus-visible:ring-gold/40 disabled:pointer-events-none"
    />
  </SliderPrimitive.Root>
))
Slider.displayName = 'Slider'

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      'flex h-9 items-center justify-between gap-2 rounded bg-sunken px-3',
      'border border-line/8 text-sm text-ink shadow-sm',
      'transition-[border-color,box-shadow] duration-fast',
      'hover:border-line/14',
      'focus:outline-none focus:ring-2 focus:ring-gold/20 focus:border-gold/40',
      'disabled:opacity-40 [&>span]:truncate',
      className,
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="size-3.5 shrink-0 text-ink-4" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = 'SelectTrigger'

export const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      position={position}
      className={cn(
        'relative z-50 max-h-72 min-w-[8rem] overflow-hidden rounded-lg',
        'border border-line/10 bg-overlay shadow-xl',
        'data-[state=open]:animate-scale-in',
        position === 'popper' && 'translate-y-1',
        className,
      )}
      {...props}
    >
      <SelectPrimitive.Viewport className="p-1">
        {children}
      </SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = 'SelectContent'

export const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      'relative flex cursor-pointer select-none items-center gap-2',
      'rounded-sm py-1.5 pl-7 pr-2 text-sm text-ink-2 outline-none',
      'transition-colors duration-fast',
      'data-[highlighted]:bg-ink/[0.06] data-[highlighted]:text-ink',
      'data-[state=checked]:text-ink',
      'data-[disabled]:pointer-events-none data-[disabled]:opacity-40',
      className,
    )}
    {...props}
  >
    <span className="absolute left-2 flex size-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="size-3.5 text-gold" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = 'SelectItem'

export const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = 'horizontal', ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    orientation={orientation}
    className={cn(
      'shrink-0 bg-line/8',
      orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
      className,
    )}
    {...props}
  />
))
Separator.displayName = 'Separator'

export const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    className={cn('relative overflow-hidden', className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="size-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollAreaPrimitive.Scrollbar
      orientation="vertical"
      className="flex w-2 touch-none select-none p-0.5
                 transition-opacity duration-normal data-[state=hidden]:opacity-0"
    >
      <ScrollAreaPrimitive.Thumb className="flex-1 rounded-full bg-ink/[0.16]" />
    </ScrollAreaPrimitive.Scrollbar>
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
))
ScrollArea.displayName = 'ScrollArea'

/* ==========================================================================
   Progress: bar and ring
   ========================================================================== */

export function ProgressBar({
  value,
  className,
  tone = 'gold',
}: {
  value: number
  className?: string
  tone?: 'gold' | 'indigo' | 'success'
}) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div
      className={cn('h-1 w-full overflow-hidden rounded-full bg-ink/[0.09]',
                    className)}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn(
          'h-full rounded-full transition-[width] duration-slow ease-out',
          { gold: 'bg-gold', indigo: 'bg-indigo', success: 'bg-success' }[tone],
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

/**
 * A progress ring. `stroke-dashoffset` animates on the same curve as
 * everything else, so the number and the arc arrive together.
 */
export function ProgressRing({
  value,
  size = 72,
  stroke = 6,
  label,
  sublabel,
  tone = 'gold',
  className,
}: {
  value: number
  size?: number
  stroke?: number
  label?: string
  sublabel?: string
  tone?: 'gold' | 'indigo' | 'success'
  className?: string
}) {
  const pct = Math.max(0, Math.min(100, value))
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const colour = { gold: 'stroke-gold', indigo: 'stroke-indigo',
                   success: 'stroke-success' }[tone]
  return (
    <div
      className={cn('relative shrink-0', className)}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-ink/[0.09]"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (pct / 100) * circumference}
          className={cn(colour, 'transition-[stroke-dashoffset] duration-slow ease-out')}
        />
      </svg>
      {label ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-md font-semibold tabular text-ink leading-none">
            {label}
          </span>
          {sublabel ? (
            <span className="mt-0.5 text-2xs text-ink-4">{sublabel}</span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

/* ==========================================================================
   Skeleton and empty state
   ========================================================================== */

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('skeleton', className)} {...props} />
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-16 text-center',
        className,
      )}
    >
      {icon ? (
        <div
          className="mb-1 flex size-12 items-center justify-center rounded-xl
                     border border-line/8 bg-card text-ink-4 shadow-sm
                     [&_svg]:size-5"
        >
          {icon}
        </div>
      ) : null}
      <div className="max-w-sm space-y-1.5">
        <h3 className="text-md font-semibold text-ink-2">{title}</h3>
        {description ? (
          <p className="text-sm leading-relaxed text-ink-4">{description}</p>
        ) : null}
      </div>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}
