'use client'

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

/**
 * The press animation is the detail that sells this: `active:scale-[0.97]` on
 * a 120ms curve reads as a physical button rather than a coloured rectangle.
 * Every variant shares it, so the whole app feels like one piece of software.
 */
const buttonVariants = cva(
  [
    'relative inline-flex items-center justify-center gap-1.5 whitespace-nowrap',
    'font-medium select-none',
    'transition-[background-color,color,box-shadow,transform,border-color]',
    'duration-fast ease-out',
    'active:scale-[0.97]',
    'disabled:pointer-events-none disabled:opacity-40',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60',
    'focus-visible:ring-offset-2 focus-visible:ring-offset-canvas',
    '[&_svg]:shrink-0 [&_svg]:size-[1.05em]',
  ],
  {
    variants: {
      variant: {
        // The one primary action on a screen. Gold, and used sparingly.
        primary:
          'bg-gold-sheen text-canvas shadow-sm hover:brightness-110 ' +
          'hover:shadow-glow font-semibold',
        // The workhorse.
        secondary:
          'bg-raised text-ink border border-line/10 shadow-sm ' +
          'hover:bg-raised hover:border-line/20 hover:brightness-110',
        // Sits on a card without competing with it.
        ghost:
          'text-ink-2 hover:bg-ink/[0.06] hover:text-ink',
        // Sidebar and toolbar items.
        quiet:
          'text-ink-3 hover:bg-ink/[0.05] hover:text-ink-2',
        outline:
          'border border-line/14 text-ink-2 hover:border-line/24 ' +
          'hover:text-ink hover:bg-ink/[0.03]',
        danger:
          'bg-danger/12 text-danger border border-danger/22 ' +
          'hover:bg-danger/18 hover:border-danger/34',
        accent:
          'bg-indigo-sheen text-white shadow-sm hover:brightness-110',
        link: 'text-gold underline-offset-4 hover:underline active:scale-100',
      },
      size: {
        xs: 'h-6 px-2 text-2xs rounded-sm gap-1',
        sm: 'h-7.5 px-2.5 text-xs rounded-sm',
        md: 'h-9 px-3.5 text-sm rounded',
        lg: 'h-11 px-5 text-md rounded-lg',
        icon: 'size-9 rounded p-0',
        'icon-sm': 'size-7.5 rounded-sm p-0',
        'icon-lg': 'size-11 rounded-lg p-0',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
  /** Right-aligned shortcut hint, e.g. "⌘K". */
  kbd?: string
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, asChild = false, loading, kbd, children,
      disabled, ...props },
    ref,
  ) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <Loader2 className="animate-spin" aria-hidden />
            <span className="sr-only">Working</span>
          </>
        ) : null}
        {children}
        {kbd ? (
          <kbd
            className="ml-1.5 rounded-[4px] border border-line/12 bg-ink/[0.04]
                       px-1 py-px font-mono text-2xs text-ink-3 tabular"
          >
            {kbd}
          </kbd>
        ) : null}
      </Comp>
    )
  },
)
Button.displayName = 'Button'

export { buttonVariants }
